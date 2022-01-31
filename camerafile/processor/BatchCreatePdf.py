from camerafile.core.BatchTool import TaskWithProgression
from camerafile.core.Logging import Logger
from camerafile.tools.PdfFile import PdfFile

LOGGER = Logger(__name__)


# Not compatible with multi sub-processes
class BatchCreatePdf(TaskWithProgression):

    def __init__(self, media_set):
        self.media_set = media_set
        self.pdf_file = PdfFile(str(media_set.output_directory.path / "index-all.pdf"))
        TaskWithProgression.__init__(self, batch_title="Generate a pdf file with all thumbnails", nb_sub_process=0)

    def initialize(self):
        LOGGER.write_title(self.media_set, self.update_title())

    def task_getter(self):
        return self.task

    def task(self, current_media):
        self.pdf_file.add_media_image(current_media)

    def arguments(self):
        return self.media_set.get_date_sorted_media_list()

    def post_task(self, result, progress_bar, replace=False):
        progress_bar.increment()

    def finalize(self):
        LOGGER.info("No thumbnail found for " + str(self.pdf_file.no_thb) + " files")
        self.pdf_file.save()
