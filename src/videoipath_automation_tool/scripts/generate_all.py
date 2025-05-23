from videoipath_automation_tool.scripts.generate_driver_models import DEFAULT_OUTPUT_FILE, DEFAULT_SCHEMA_FILE, parser
from videoipath_automation_tool.scripts.generate_driver_models import main as generate_driver_models
from videoipath_automation_tool.scripts.generate_overloads import main as generate_overloads


def main(
    schema_file: str = DEFAULT_SCHEMA_FILE,
    output_file: str = DEFAULT_OUTPUT_FILE,
):
    generate_driver_models(schema_file, output_file)
    generate_overloads()


if __name__ == "__main__":
    args = parser.parse_args()
    main(args.schema_file, args.output_file)
