# Installation

## Requirements

- Python 3.10 or newer.
- For PDF generation: WeasyPrint 70.0 and its native Pango/font runtime.

HTML rendering, JSON validation, schema export and normalization do not require WeasyPrint.
The package does not require a web framework, database or application server.

## Install with pip

Install the package from your configured Python package index:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install smd-reports
```

On Windows, activate the environment with `.venv\Scripts\activate` instead.
Pip uses PyPI by default. For private distribution, configure pip to use your
organization's package index. The package version must be available on that index before pip can install it.

To generate PDFs in the same environment:

```sh
python -m pip install "smd-reports[pdf]"
```

## Pin a release

For reproducible application deployments, pin the reviewed package version:

```sh
python -m pip install "smd-reports==0.4.0"
# With PDF support:
python -m pip install "smd-reports[pdf]==0.4.0"
```

Use the same requirement in your application's dependency configuration. To upgrade
to the latest available release:

```sh
python -m pip install --upgrade smd-reports
```

## Native PDF dependencies

The `pdf` extra installs Python dependencies, not operating-system libraries. On
Debian 12+ or Ubuntu 24.04+, an administrator can install the native libraries with:

```sh
sudo apt-get update
sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0
```

HarfBuzz-Subset 4.1.0 or newer is required for native font subsetting. When the library
is missing or too old, WeasyPrint 70.0 uses fontTools and logs a warning for each font.
Install or upgrade the native library and restart the application process to load it.
Ubuntu 22.04 ships HarfBuzz 2.7.4 and does not provide this subset package. Use a newer
rendering environment, such as an Ubuntu 24.04 container, for native font subsetting.
WeasyPrint 70.0 can still generate PDFs on the older runtime using its fontTools fallback.
A pip upgrade alone does not install this operating-system dependency. See the
[WeasyPrint installation guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation)
for platform-specific packages.

Installation methods differ on other operating systems. Prepare the native runtime
before calling `render_pdf()`. Missing Python/native renderer dependencies raise
`PDFUnavailableError`; install both the extra and the native libraries to resolve it.

The extra pins WeasyPrint 70.0. If an application already pins another version, resolve
that dependency choice and verify its PDF output before upgrading the environment.

## Verify the installation

```sh
python -c 'import smd_reports; print(smd_reports.__version__)'
python -m smd_reports --help
smd-reports --help
```

Continue with the [quickstart](quickstart.md). For an editable source checkout and
documentation development, see [contributing](contributing.md).
