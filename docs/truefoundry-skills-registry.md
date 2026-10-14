# TrueFoundry Skills Registry

The skills in this repository are portable `SKILL.md` bundles. [TrueFoundry Skills Registry](https://www.truefoundry.com/docs/ai-gateway/skills/skills-registry) is the catalog for sharing a reviewed copy with more than one agent. The launch note and the longer explainer are [Introducing Skills Registry](https://www.truefoundry.com/blog/introducing-skills-registry-reusable-agent-skills-for-production-ai-systems) and [TrueFoundry Skills Registry, Explained](https://www.truefoundry.com/blog/truefoundry-skills-registry-explained).

## What the registry does

A skill is stored in a repository, with prompts and models. That repository is the scope for who can discover the skill, edit it, and attach it. It also keeps the version history and the audit log.

Each publish is a numbered version. In the agent builder, an agent can follow the current version or pin an older one. Pinning is how you roll back a publish that misbehaves.

A single `SKILL.md` can be written in the UI. The Linear and Slack bundles here are an index plus reference files, so they are published as a multi-file bundle with the TrueFoundry CLI or with GitOps `tfy apply`.

At runtime the agent sees the skill name and description first and loads the body when that skill applies. A short skill that should always be in view can be preloaded instead.

The same published version can be attached to a TrueFoundry Agent or pulled into Claude Code and Cursor.

## What the registry does not do

The registry distributes the procedural bundle. It does not grant credentials, allow a tool, approve a write, or execute a call. Those controls belong to [TrueFoundry MCP Gateway](https://www.truefoundry.com/mcp-gateway) and to the target system. A skill can tell an agent which Linear or Slack tool to choose. The gateway and the product still decide whether that call is allowed.
