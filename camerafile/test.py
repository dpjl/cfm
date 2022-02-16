import argparse


def create_args_parser():
    args_parser = argparse.ArgumentParser(description="<Main description of the tool>")

    sp_list = args_parser.add_subparsers(title="Subcommands list",
                                         description="Use '<command> -h' to display the help of a specific command",
                                         dest='command')

    p = sp_list.add_parser("create", help="'create' command description")
    p.add_argument('S3Bucketname', metavar='dir1', type=str, help="<help for this argument>")
    p.add_argument('foldername', nargs='?', metavar='dir2', type=str, help="<help for this argument>")

    p = sp_list.add_parser("delete", help="'delete' command description")
    p.add_argument('S3Bucketname', metavar='dir1', type=str, help="<help for this argument>")
    p.add_argument('foldername', nargs='?', metavar='dir2', type=str, help="<help for this argument>")

    p = sp_list.add_parser("show", help="'show' command description")
    p.add_argument('S3Bucketname', metavar='dir1', type=str, help="<help for this argument>")
    p.add_argument('output_foldername', nargs='?', metavar='dir2', type=str, help="<help for this argument>")

    p = sp_list.add_parser("download", help="'download' a media set")
    p.add_argument('S3Bucketname', metavar='dir1', type=str, help="<help for this argument>")
    p.add_argument('results_foldername', nargs='?', metavar='dir2', type=str, help="<help for this argument>")

    return args_parser


if __name__ == '__main__':
    parser = create_args_parser()
    args = parser.parse_args()
