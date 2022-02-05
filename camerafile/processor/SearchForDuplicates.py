from camerafile.console.ConsoleTable import ConsoleTable
from camerafile.core.Logging import Logger
from camerafile.core.MediaSet import MediaSet
from camerafile.processor.BatchComputeNecessarySignaturesMultiProcess import BatchComputeNecessarySignaturesMultiProcess
from camerafile.tools.PdfFile import PdfFile

LOGGER = Logger(__name__)


class SearchForDuplicates:

    @staticmethod
    def execute(media_set: MediaSet):

        BatchComputeNecessarySignaturesMultiProcess(media_set).execute()

        duplicates = media_set.duplicates()
        duplicates_report = media_set.get_duplicates_report(duplicates)

        LOGGER.display_starting_line()
        print("█ Found duplicates:")
        tab = ConsoleTable()
        tab.print_header(str(media_set.root_path))
        tab.print_multi_line(duplicates_report)

        if True:
            pdf_file = PdfFile(str(media_set.output_directory.path / "duplicates.pdf"))

            for n_copy, media_list_list in sorted(duplicates.items()):
                if n_copy != 1:
                    for media_list in media_list_list:
                        for media in media_list:
                            pdf_file.add_media_image(media)
                        pdf_file.new_line()

            pdf_file.save()

        pdf_file = PdfFile(str(media_set.output_directory.path / "edited.pdf"))

        for date in media_set.date_model_size_map:
            for model in media_set.date_model_size_map[date]:
                if model is not None and model != "" and len(media_set.date_model_size_map[date][model]) > 1:
                    for dim in media_set.date_model_size_map[date][model]:
                        for media in media_set.date_model_size_map[date][model][dim]:
                            pdf_file.add_media_image(media)
                            break
                    pdf_file.new_line()

        pdf_file.save()
