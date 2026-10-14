# Skills

The current skills are progressive bundles. `SKILL.md` is a short index the agent can keep in view. Files under `references/` are opened only after the index has chosen an object.

| Bundle | Directory | Frontmatter name | Install directory |
| --- | --- | --- | --- |
| Linear | `skills/linear/` | `linear-app-skill` | `.cursor/skills/linear-app-skill/` |
| Slack | `skills/slack/` | `slack-skill` | `.cursor/skills/slack-skill/` |

Linear references cover planning objects, issues, content, and reviews. Slack references cover finding conversations, writes, and artifacts such as canvases, lists, and files.

## Use them in Cursor

From the repository root:

```bash
mkdir -p .cursor/skills
cp -R skills/linear .cursor/skills/linear-app-skill
cp -R skills/slack .cursor/skills/slack-skill
```

The same directories can be copied to `~/.cursor/skills/` for every project. The benchmark treatment installs one bundle at a time under the directory name in the table. The frontmatter `name` must keep matching that directory.

Publishing these bundles for more than one agent is covered in [`docs/truefoundry-skills-registry.md`](../docs/truefoundry-skills-registry.md).
