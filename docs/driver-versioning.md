
# Driver Versioning

Driver schemas are auto-generated from the VideoIPath API's JSON schema, enabling IntelliSense support during development and runtime validation of custom settings.

By default, the system uses the latest Long-Term Support (LTS) version, currently **2024.4.30**.

To switch to a different version after installation, run:

```bash
set-videoipath-version <version>
```

For example:

```bash
set-videoipath-version 2024.3.3
```

If no version is specified, the latest available LTS version is automatically used.

To view the currently active version, use:

```bash
get-videoipath-version
```

To list all available versions, run:

```bash
list-videoipath-versions
```
