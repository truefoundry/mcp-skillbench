# Planning objects

Read this after choosing a cycle, project, milestone, or initiative. The index already decides which level; this file covers filters the schema does not make obvious.

## Cycles

`list_cycles` `teamId` is a team id, not a team name. Resolve the name with `list_teams` first. `type` of `current`, `previous`, or `next` is this, last, or next sprint.

## Projects

`get_project` looks up one project. Its identifier argument is named `query` and accepts a name, id, or slug. It is an exact lookup, not a search across projects. `list_projects` is the set and name search.

## Milestones

`list_milestones`, `get_milestone`, and `save_milestone` require the parent `project`. A milestone is a checkpoint inside that project, not a project or a cycle.

## Initiatives

`list_initiatives` is the set of themes above projects. `get_initiative` is one theme. Do not pass a project name here.
