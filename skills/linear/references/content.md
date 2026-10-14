# Documents and attachments

Read this after choosing a workspace document, Linear help docs, or a file attachment.

## Documents

`list_documents` filters (`projectId`, `teamId`, `initiativeId`, `creatorId`) are ids. A name is rejected; resolve it first. Rows in the list truncate `content`. The full body comes from `get_document`.

`save_document` requires `title` and exactly one parent (`project`, `issue`, `initiative`, `cycle`, or `team`) when creating. Passing a parent on update moves the document.

`search_documentation` searches Linear's own product and API docs. It does not search documents the workspace wrote.

## File attachments

A URL on an issue uses `save_issue` `links`. A file uses this sequence:

1. `prepare_attachment_upload` with the issue, filename, content type, and exact byte size. It returns `uploadRequest` and `assetUrl`.
2. PUT the raw bytes to `uploadRequest.url`. Send every signed header verbatim, including header casing. The URL expires in about 60 seconds. Do not base64-encode the body.
3. `create_attachment_from_upload` with `assetUrl`. This only creates the Linear record. If the PUT failed or expired, start again at step 1.

`create_attachment` is the deprecated base64 fallback. Use it only when the signed upload is unavailable, and only for a tiny file.

`extract_images` takes the markdown that contains the image, not an issue id. Fetch the description, comment, or document first.
