import json

from videoipath_automation_tool.apps.inventory.model.generate.driver_model_generator import DriverModelGenerator

if __name__ == "__main__":
    schema = json.load(open("src/videoipath_automation_tool/apps/inventory/model/driver_schema/2024.3.3.json"))
    DriverModelGenerator(schema=schema).generate()
