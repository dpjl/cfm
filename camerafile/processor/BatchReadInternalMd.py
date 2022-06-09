from camerafile.console.ConsoleTable import ConsoleTable
from camerafile.processor.BatchTool import BatchElement, TaskWithProgression
from camerafile.core.Configuration import Configuration
from camerafile.core.Constants import INTERNAL, THUMBNAIL
from camerafile.core.Logging import Logger
from camerafile.core.MediaSet import MediaSet
from camerafile.core.OutputDirectory import OutputDirectory
from camerafile.metadata.Metadata import Metadata
from camerafile.processor.CFMBatch import CFMBatch
from camerafile.task.LoadInternalMetadata import LoadInternalMetadata

LOGGER = Logger(__name__)


class BatchReadInternalMd(TaskWithProgression):

    def __init__(self, media_set: MediaSet, other_needed_md):
        self.media_set = media_set
        self.stats = {}
        self.call_info = {}
        self.other_needed_md = other_needed_md
        TaskWithProgression.__init__(self, "Read media exif metadata",
                                     Configuration.get().nb_sub_process,
                                     on_worker_start=BatchReadInternalMd.on_sub_cfm_start,
                                     on_worker_end=CFMBatch.on_sub_cfm_end,
                                     stderr_file=OutputDirectory.get(media_set.root_path).batch_stderr,
                                     stdout_file=OutputDirectory.get(media_set.root_path).batch_stdout)

    @staticmethod
    def on_sub_cfm_start(md_needed):
        CFMBatch.on_sub_cfm_start()
        LoadInternalMetadata.md_needed = md_needed

    def initialize(self):
        LOGGER.write_title(self.media_set, self.update_title())
        needed_md = ()
        for md in self.media_set.md_needed + self.other_needed_md:
            if md not in needed_md:
                needed_md += (md,)
        print("Metadata that need to be loaded: " + str(needed_md))
        LoadInternalMetadata.md_needed = needed_md
        self.custo_ows_args = (needed_md,)

    def task_getter(self):
        return LoadInternalMetadata.execute

    def update_stats(self, metadata_internal: Metadata, metadata_thumbnail: Metadata):
        if metadata_internal.value:
            for name, value in metadata_internal.value.items():
                if name not in self.stats:
                    self.stats[name] = 0
                if value is not None:
                    self.stats[name] += 1
        if metadata_thumbnail.thumbnail:
            if "thumbnail" not in self.stats:
                self.stats["thumbnail"] = 0
            self.stats["thumbnail"] += 1

    def update_call_info(self, call_info):
        if call_info not in self.call_info:
            self.call_info[call_info] = 0
        self.call_info[call_info] += 1

    def arguments(self):
        args_list = []
        for media_file in self.media_set:
            if media_file.metadata[INTERNAL].value is None or self.media_set.read_md_needed:
                args_list.append(
                    BatchElement((self.media_set.root_path, media_file.file_desc, media_file.metadata[INTERNAL]),
                                 media_file.get_path()))
            else:
                self.update_stats(media_file.metadata[INTERNAL], media_file.metadata[THUMBNAIL])
        return args_list

    def post_task(self, result, progress_bar, replace=False):
        media_id, modified_metadata = result
        self.update_call_info(modified_metadata.call_info)
        original_media = self.media_set.get_media(media_id)
        if replace:
            original_media.metadata[INTERNAL] = modified_metadata
        original_media.metadata[THUMBNAIL].thumbnail = original_media.metadata[INTERNAL].thumbnail
        original_media.metadata[INTERNAL].thumbnail = None
        original_media.parent_set.add_to_date_size_name_map(original_media)
        self.update_stats(modified_metadata, original_media.metadata[THUMBNAIL])
        # in case signature was already existing, but date was not, we update date_sig map
        self.media_set.add_to_date_sig_map(original_media)
        progress_bar.increment()

    def finalize(self):

        print("")
        tab = ConsoleTable()
        tab.print_header("Metadata", "Number of files")
        for key, value in self.stats.items():
            if value != 0:
                tab.print_line(key, str(value))
        print("")

        print("")
        tab = ConsoleTable()
        tab.print_header("Call", "Number of files")
        for key, value in self.call_info.items():
            tab.print_line(key, str(value))
        print("")

        self.media_set.update_loaded_metadata()
