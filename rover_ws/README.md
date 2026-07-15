# Rover WS
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new?hide_repo_select=true&repo=1162024079&skip_quickstart=true&ref=ros/dev&devcontainer_path=.devcontainer/rover_ws-pixi/devcontainer.json)

This folder covers the Rover sub-project, which is responsible for the high level control code that lives inside the on-board computer.

## Tech Stack

- ROS2 (Jazzy)
    - Using the RoboStack Conda distribution channel [↗️](https://robostack.github.io/GettingStarted.html)
- Pixi, for cross-platform ROS2 and Python package management [↗️](https://pixi.prefix.dev/latest/robotics/)

## Contributing

### Project Setup

After cloning the mono-repo, open the `rover_ws/` folder inside your favorite text editor or IDE.

### Pre-requisites

#### Installing Pixi [↗️](https://pixi.prefix.dev/latest/installation/)

Windows
```pwsh
winget install prefix-dev.pixi
```

Linux/ MacOS
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

### Devcontainer

To open this project's devcontainer locally, navigate to the [monorepo root](../) and choose the configuration under [`.devcontainer/rover_ws-pixi/`](../.devcontainer/rover_ws-pixi/).

You can also open the devcontainer via [GitHub Codespaces ↗️](https://github.com/codespaces/new?hide_repo_select=true&repo=1162024079&skip_quickstart=true&ref=ros/dev&devcontainer_path=.devcontainer/rover_ws-pixi/devcontainer.json).

> [!WARNING]
> Note that GitHub Codespaces will be difficult to configure for ROS2-based communication. For these tasks, please use develop locally even if using the devcontainer.
