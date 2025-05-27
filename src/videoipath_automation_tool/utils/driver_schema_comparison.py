import os
from typing import Any, Dict, List

from deepdiff import DeepDiff

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_driver_schema_from_file(version: str) -> list[dict]:
    schema_dir = os.path.join(ROOT_DIR, "apps", "inventory", "model", "driver_schema")
    file_path = os.path.join(schema_dir, f"{version}.json")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Schema file for version {version} does not exist.")

    with open(file_path, "r", encoding="utf-8") as file:
        import json

        parsed_schema = json.load(file)
        try:
            return parsed_schema["data"]["status"]["system"]["drivers"]["_items"]
        except KeyError as e:
            raise KeyError(f"Expected schema format not found: {e}")


class DriverSchemaComparator:
    @staticmethod
    def _reduce_driver_entry(entry):
        """
        Reduces the entry to only include _id, and customSettings, which are the fields we are interested in.
        """
        return {"_id": entry.get("_id"), "customSettings": entry.get("customSettings")}

    @staticmethod
    def _standardize_options(obj):
        """
        Standardizes the 'options' field in the '_schema' dictionary of each entry.
        If 'options' is not present, it initializes it as an empty list.
        This is to ensure compatibility with older versions of the schema.
        """
        if isinstance(obj, dict):
            if "_schema" in obj and isinstance(obj["_schema"], dict):
                obj["_schema"].setdefault("options", [])
            for value in obj.values():
                DriverSchemaComparator._standardize_options(value)
        elif isinstance(obj, list):
            for item in obj:
                DriverSchemaComparator._standardize_options(item)

    @staticmethod
    def _process_driver_schema_entries(schema):
        """
        Prepares the schema for comparison by reducing each entry to only the relevant fields and standardizing options.
        """
        reduced_schema = []
        for entry in schema:
            reduced_entry = DriverSchemaComparator._reduce_driver_entry(entry)
            DriverSchemaComparator._standardize_options(reduced_entry)
            reduced_schema.append(reduced_entry)
        return reduced_schema

    @staticmethod
    def _map_drivers_by_id(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Maps a list of driver items to a dictionary keyed by their "_id" field.
        This simplifies comparison by ensuring each item can be uniquely identified.
        """
        return {item["_id"]: item for item in items if "_id" in item}

    @staticmethod
    def _get_added_drivers(compare: dict, reference: dict) -> list:
        return sorted(set(compare) - set(reference))

    @staticmethod
    def _get_removed_drivers(compare: dict, reference: dict) -> list:
        return sorted(set(reference) - set(compare))

    @staticmethod
    def _get_changed_drivers(compare: Dict[str, dict], reference: Dict[str, dict]) -> Dict[str, dict]:
        common_ids = set(compare) & set(reference)
        changed = {}

        for driver_id in common_ids:
            diff = DeepDiff(
                reference[driver_id],
                compare[driver_id],
                ignore_order=True,
                view="tree",
            )
            if not diff:
                continue

            descriptor_diff = DriverSchemaComparator._extract_descriptor_changes(diff)
            custom_changes = DriverSchemaComparator._extract_custom_settings_changes(diff)
            detailed_diffs = DriverSchemaComparator._extract_detailed_custom_diffs(
                compare[driver_id], reference[driver_id]
            )

            entry = {}
            if descriptor_diff:
                entry["descriptor"] = descriptor_diff

            if custom_changes or detailed_diffs:
                entry["customSettings"] = {}
                if custom_changes:
                    entry["customSettings"].update(custom_changes)
                if detailed_diffs:
                    entry["customSettings"]["changed"] = detailed_diffs

            changed[driver_id] = entry

        return changed

    @staticmethod
    def _extract_descriptor_changes(diff: DeepDiff) -> dict:
        descriptor_changes = {}

        for item in diff.get("values_changed", []):
            path = item.path(output_format="list")
            if path[:2] == ["descriptor", "label"]:
                descriptor_changes["label"] = {
                    "old": item.t1,
                    "new": item.t2,
                }
            elif path[:2] == ["descriptor", "desc"]:
                descriptor_changes["desc"] = {
                    "old": item.t1,
                    "new": item.t2,
                }

        return descriptor_changes

    @staticmethod
    def _extract_custom_settings_changes(diff: DeepDiff) -> dict:
        added, removed = set(), set()

        for item in diff.get("dictionary_item_added", []):
            path = item.path(output_format="list")
            if len(path) >= 4 and path[:3] == ["customSettings", "_schema", "values"]:
                added.add(path[3])

        for item in diff.get("dictionary_item_removed", []):
            path = item.path(output_format="list")
            if len(path) >= 4 and path[:3] == ["customSettings", "_schema", "values"]:
                removed.add(path[3])

        result = {}
        if added:
            result["added"] = sorted(added)
        if removed:
            result["removed"] = sorted(removed)

        return result

    @staticmethod
    def _extract_detailed_custom_diffs(compare_entry: dict, reference_entry: dict) -> dict:
        """
        Compares each individual setting's _schema in customSettings._schema.values.
        Returns detailed differences for shared setting keys.
        """
        result = {}

        reference_values = reference_entry.get("customSettings", {}).get("_schema", {}).get("values", {})
        compare_values = compare_entry.get("customSettings", {}).get("_schema", {}).get("values", {})

        shared_keys = set(reference_values) & set(compare_values)

        for key in shared_keys:
            reference_custom_settings = reference_values[key]["_schema"]
            compare_custom_settings = compare_values[key]["_schema"]

            diff = DeepDiff(reference_custom_settings, compare_custom_settings, ignore_order=True)
            if diff:
                detailed = {}

                if "values_changed" in diff:
                    for path, change in diff["values_changed"].items():
                        short_path = path.replace("root['", "").replace("']", "").replace("']['", ".")
                        detailed[short_path] = {
                            "old": change["old_value"],
                            "new": change["new_value"],
                        }

                if "iterable_item_removed" in diff:
                    detailed["removed_items"] = diff["iterable_item_removed"]

                if "iterable_item_added" in diff:
                    detailed["added_items"] = diff["iterable_item_added"]

                result[key] = detailed

        return result

    @staticmethod
    def compare_driver_schemas(compare_schema: list[dict], reference_schema: list[dict]) -> dict:
        """
        Compares two driver schemas and returns a summary of changes.

        Args:
            compare_schema (list[dict]): The schema to compare against the reference.
            reference_schema (list[dict]): The reference schema to compare with.
        """
        compare = DriverSchemaComparator._map_drivers_by_id(
            DriverSchemaComparator._process_driver_schema_entries(compare_schema)
        )
        reference = DriverSchemaComparator._map_drivers_by_id(
            DriverSchemaComparator._process_driver_schema_entries(reference_schema)
        )

        return {
            "added_drivers": DriverSchemaComparator._get_added_drivers(compare, reference),
            "removed_drivers": DriverSchemaComparator._get_removed_drivers(compare, reference),
            "changed_drivers": DriverSchemaComparator._get_changed_drivers(compare, reference),
        }

    @staticmethod
    def missmatch_in_driver_schema(comparison_result: dict) -> bool:
        """
        Checks if there are any mismatches in the comparison result.
        Returns True if there are mismatches, otherwise False.
        """
        return (
            bool(comparison_result["added_drivers"])
            or bool(comparison_result["removed_drivers"])
            or bool(comparison_result["changed_drivers"])
        )
