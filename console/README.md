# Console
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new?hide_repo_select=true&repo=1162024079&skip_quickstart=true&ref=console/dev&devcontainer_path=.devcontainer/console/devcontainer.json)

This is the Console sub-project folder, containing the source code for the remote-control GUI.

## Contributing

### Project Setup

After cloning the mono-repo, open the `console/` folder inside your favorite text editor or IDE.

### Pre-requisites

#### Installing Pixi [↗️](https://pixi.prefix.dev/latest/installation/)

**Windows**
Pixi
```pwsh
winget install prefix-dev.pixi
```
and MSVC
```pwsh
winget install --id Microsoft.VisualStudio.2022.BuildTools --source winget --force --accept-package-agreements --accept-source-agreements --override "--add Microsoft.VisualStudio.Workload.VCTools --includeRecommended --wait /norestart"
```


**Linux/ MacOS**
```sh
curl -fsSL https://pixi.sh/install.sh | bash
```

#### Installing project dependencies

Make sure you are in a pixi-activated shell
```sh
pixi shell
```

Then, run:
```sh
pixi install
```

Then:
```sh
colcon build
```

### Startup

run:
```sh
pixi run console
```

### Devcontainer

To open this project's devcontainer locally, navigate to the [monorepo root](../) and choose the configuration under [`.devcontainer/console/`](../.devcontainer/console/).

You can also open the devcontainer via [GitHub Codespaces ↗️](https://github.com/codespaces/new?hide_repo_select=true&repo=1162024079&skip_quickstart=true&ref=console/dev&devcontainer_path=.devcontainer/console/devcontainer.json).

> [!WARNING]
> Note that GitHub Codespaces will be very difficult to configure for desktop UI application development, joystick device input, and ROS2-based communication. For these tasks, please use develop locally even if using the devcontainer.