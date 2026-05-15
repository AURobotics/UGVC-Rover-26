# UGVC-Rover-26

This is the mono-repo for our participation in the UGVC 2026 competition organized by ICMTC in Egypt.

## Contributing

### Project Navigation

This is a mono-repo. Every folder at the mono-repo root level is considered a separate sub-project.

#### Opening a project

It is **not** recommended to directly open the mono-repo root folder in your text editor or IDE. Please open the sub-project folder for the project you are working on.

#### Project list

| Project  | Description                                                                  |
|----------|------------------------------------------------------------------------------|
| console  | GUI for remote control                                                       |
| firmware | firmware for the on-board MCUs                                               |
| network  | configuration and scripts for network setup                                  |
| reports  | deliverable documents required by the competition                            |
| rover_ws | ROS2 project for on-board control, navigation, vision and communication |
| station  | router configuration and firmware for the direction controller               |


### Cross-project Work

Since this is a mono-repo, simultaneously updating different sub-projects (e.g `rover_ws` and `console`) will require working with more than one branch at a time.

#### Git Worktrees [↗️](https://git-scm.com/docs/git-worktree)

Git worktrees work as a direct alternative to cloning the repo twice to work on it in parallel.

Under the mono-repo root folder `UGVC-Rover-26` run:
```sh
git worktree add ../UGVC-Rover-26-WT-[Reason] <branch-name>
```

Replace `[Reason]` with a short, descriptive name you can refer to later. Replace `<branch-name>` with the other branch you want to work on in parallel. Append `-b` to the command if you want to create a new branch with name `branch-name`.

You can now treat `UGVC-Rover-26-WT-[Reason]` as a new clone of the mono-repo, and open the sub-project folder from it in your favorite text editor or IDE.