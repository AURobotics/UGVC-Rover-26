# UGVC-Rover-26

This is the monorepo for our participation in the UGVC 2026 competition organized by ICMTC in Egypt.

## Contributing

### Project Navigation

This is a monorepo. Every folder at the monorepo root level is considered a separate subproject.

#### Opening a project

It is **not** recommended to directly open the monorepo root folder in your text editor or IDE. Please open the subproject folder for the project you are working on.

#### Project list

| Project                 | Base Branch        | Description                                                             |
|-------------------------|--------------------|-------------------------------------------------------------------------|
| [Monorepo](./)           | `main` | structuring of the monorepo                                             |
| [console](./console/)   | `console/dev`      | GUI for remote control                                                  |
| [firmware](./firmware/) | `firmware/dev`     | firmware for the on-board MCUs                                          |
| [network](./network/)   | `network/dev`      | configuration and scripts for network setup                             |
| [reports](./reports/)   | `reports/dev`      | deliverable documents required by the competition                       |
| [rover_ws](./rover_ws/) | `ros/dev`          | ROS2 project for on-board control, navigation, vision and communication |
| [field](./field/)       | `field/dev`      | firmware & configuration for on-field devices, ex: router & killswitch  |


### Branch Strategies

Below is a graph demonstrating the branch strategies for the each of the subprojects as `<project>` and for the root-level changes. 

```mermaid
graph TD

    subgraph ProjectTrack ["Contributions Pipeline"]
        direction TB
        subgraph ReviewerSyncSub ["Maintainers + Reviewers"]
            MainStart2["main"] -->|New Branch &lpar;Maintainers&rpar; or Sync &lpar;Reviewers&rpar;| ProjDev1["&lt;project&gt;/dev"]
        end
        ProjDev1 -->|New Feature Branch| ProjFeature["&lt;project&gt;/&lt;FEATURE&gt;"]
        ProjFeature -->|Open| PRStep["Feature PR"]
        
        subgraph ReviewerPrSub ["Reviewers"]
            direction TB
            ReviewStep["Feature Code Review"] -->|Approve & Merge| ProjDev2["&lt;project&gt;/dev"]
            IntegrationPR["Integration PR"]
        end ReviewerPrSub
        
        subgraph DevMaintainers ["Maintainers"]
            direction TB
            IntegrationPR -->|Trigger| FinalReview["Final Review"]
            FinalReview -->|Approve & Final Merge| MainEnd2["main"]
        end

        PRStep -->|Trigger| ReviewStep
        
        %% Flow from project dev branch into the main integration pipeline
        ProjDev2 -->|Open PR to main| IntegrationPR
    end

    classDef mainBranch fill:#070707,stroke:#373737,stroke-width:2px,color:#EDEFF0;
    classDef devBranch fill:#FA5F6C,stroke:#DD1F44,stroke-width:2px,color:#FEDFDF;
    classDef reviewNode fill:#FCA6A7,stroke:#FEDFDF,stroke-width:2px,color:#070707;

    class MainStart2,MainEnd2 mainBranch
    class ProjDev1,ProjDev2 devBranch
    class ProjFeature featureBranch
    class PRStep,ReviewStep,IntegrationPR,FinalReview reviewNode
```

#### Merge Strategy

When merging from `<feature>` into `<base>` ensure linear history.

This can be best achieved by rebasing on `<base>` before merging:
```sh
(on <feature>)$ git rebase <base>
```

According to the previous branch strategy diagram, you should follow these guidelines when merging from `<project>/<FEATURE>` into `<project>/dev` and when merging from `<project>/dev` into `main`.

Here is a detailed merge workflow that accounts for the processes of pull request reviewing, resolving conflicts and rebasing before merging:

```mermaid
graph TD
    %% Define Workflow Nodes
    Start([1. Ready to Merge]) --> CheckOutofDate{2. Is Branch Out of Date?}
    
    CheckOutofDate -->|Yes: PR shows 'Branch is out-of-date'| SyncBranch["3. Sync & Rebase Base Branch
    ───
    git checkout &lt;base&gt;
    git pull
    git checkout &lt;feature&gt;
    git rebase &lt;base&gt"]
    
    CheckOutofDate -->|No: PR shows 'All checks passed'| AskReview[4. Wait for Maintainer Review]
    
    SyncBranch --> DetectConflicts{3a. Conflicts Detected?}
    
    DetectConflicts -->|Yes: Git pauses rebase| FixConflicts["3b. Resolve Conflicts Locally
    ───
    (Fix file markers in IDE)
    git add &lt;files&gt;
    git rebase --continue"]
    
    FixConflicts --> SyncBranch
    
    DetectConflicts -->|No: Rebase successful| ForcePush["3c. Push to Remote Safely
    ───
    git push origin &lt;feature&gt; --force-with-lease"]
    
    ForcePush --> AskReview
    
    %% Review & Finalization
    AskReview --> CheckApproval{5. Review Approved?}
    
    CheckApproval -->|No: Changes Requested| DevEdits["5a. Make Code Edits Locally
    ───
    (Edit files)
    git add &lt;files&gt;
    git commit -m 'address feedback'"]
    
    DevEdits --> CheckOutofDate
    
    CheckApproval -->|Yes| FinalMerge(["6. Maintainer/Reviewer Finishes Merge
    ───
    GitHub Web UI: 'Rebase and merge'"])

    %% Styles matched to your README definitions
    classDef mainBranch fill:#070707,stroke:#373737,stroke-width:2px,color:#EDEFF0;
    classDef modificationBranch fill:#383B3D,stroke:#191B1C,stroke-width:2px,color:#EDEFF0;
    classDef devBranch fill:#FA5F6C,stroke:#DD1F44,stroke-width:2px,color:#FEDFDF;
    classDef reviewNode fill:#FCA6A7,stroke:#FEDFDF,stroke-width:2px,color:#070707;
    classDef logicGate fill:#383B3D,stroke:#FA5F6C,stroke-width:1px,color:#EDEFF0;

    class Start,FinalMerge mainBranch;
    class SyncBranch,FixConflicts,ForcePush,DevEdits modificationBranch;
    class AskReview devBranch;
    class CheckOutofDate,DetectConflicts,CheckApproval logicGate;
```


### Cross-project Work

Since this is a monorepo, simultaneously updating different subprojects (e.g `rover_ws` and `console`) will require pulling and merging more than one branch at a time.

To follow the branch and merge strategies, use the following method to help in doing so.

#### Multiple Clones | Git Worktrees [↗️](https://git-scm.com/docs/git-worktree)

You can clone the repo more than once if you are a reviewer or maintainer working on more than one branch at a time.

Git worktrees work as a direct alternative to cloning the repo twice to work on multiple branches in parallel.

Under the monorepo root folder `UGVC-Rover-26` run:
```sh
git worktree add ../UGVC-Rover-26-WT-[Reason] <branch-name>
```

Replace `[Reason]` with a short, descriptive name you can refer to later. Replace `<branch-name>` with the other branch you want to work on in parallel. Append `-b` to the command if you want to create a new branch with name `branch-name`.

You can now treat `UGVC-Rover-26-WT-[Reason]` as a new clone of the monorepo, and open the subproject folder from it in your favorite text editor or IDE.

#### Single Feature Branch for Multiple Subprojects (Discouraged)

When time is tight, you may create a branch called `feature/<FEATURE>` from one of the subprojects you are working on. Then start a pull request for that subproject and inform the reviewers of the other subprojects to review and `git cherry-pick` your relevant commits into their branch.