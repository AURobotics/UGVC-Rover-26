# Reports
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new?hide_repo_select=true&repo=1162024079&skip_quickstart=true&ref=reports/dev&devcontainer_path=.devcontainer/reports/devcontainer.json)

This folder contains source code and assets for deliverable documents required by the competition.

## Project Setup

You need a LaTeX compiler (`pdflatex`) to turn the `.tex` files into `.pdf` files.

### Dependencies

#### MiKTeX

The recommended LaTeX compiler for this repo is [MiKTeX](https://miktex.org/) since it is lightweight by default and automatically installed missing packages when you need them.

#### Perl (for Windows)

**Strawberry Perl**\
Windows does not come with perl bundled, you may install it from the [Strawberry Perl](https://strawberryperl.com/) distribution. Note that it comes with extra binaries like `gcc` that may cause version conflicts in your other projects.

**Perl from 3rd Party Package Managers**\
You may look towards package managers like scoop, chocolatey, or a conda package manager like pixi to achieve a minimal-conflict global installation of perl.

At the time of writing this guide, the chocolatey distribution of perl explicitly states that it adds binaries like `gcc` to PATH. Scoop avoids this and pixi may be used to avoid it as well.

### Using `latexmk` & `pdflatex`

#### LaTeX Workshop (VSCode)

Open the main `.tex` file and press the run button ![run icon](https://raw.githubusercontent.com/microsoft/vscode-icons/refs/heads/main/icons/dark/run.svg) or the preview button to compile to PDF.

You may also use the preview button ![preview icon](https://raw.githubusercontent.com/microsoft/vscode-icons/refs/heads/main/icons/dark/open-preview.svg) to preview the PDF in the editor.

#### Command Line

To compile a main `.tex` file, go to its directory and run
```sh
latexmk -pdf -outdir=output -auxdir=output/aux <main>.tex
```

### Devcontainer

To open this project's devcontainer locally, navigate to the [monorepo root](../) and choose the configuration under [`.devcontainer/reports/`](../.devcontainer/reports/).

You can also open the devcontainer via [GitHub Codespaces ↗️](https://github.com/codespaces/new?hide_repo_select=true&repo=1162024079&skip_quickstart=true&ref=reports/dev&devcontainer_path=.devcontainer/reports/devcontainer.json).

For easier previewing, GitHub Codespaces users are encouraged to open their Codespaces on the VSCode application.