# Security and data boundaries

- Supabase Auth manages passwords and sessions. Application tables do not store passwords.
- The API verifies identity and workspace membership. Administrator actions require that role.
- Row-level security restricts organization data and private user conversations.
- Original documents use private Storage and access-checked temporary download links.
- Invitations bind to an email, expire after seven days, and allow a single acceptance.
- Email requests and workspace questions have durable limits.
- Extraction rejects unsafe archives and excessive expansion and runs in a bounded subprocess.
- Only public Supabase configuration and the user's own session reach the browser. Server keys remain in ignored environment files or hosting secrets.
- Retrieved documents are untrusted data. The answer prompt instructs the model to ignore document instructions and use authorized evidence.

The release makes no enterprise security-certification claim. Review provider data policy before uploading sensitive documents. Citation checks do not establish factual correctness.

Report issues through the repository tracker without including credentials, private documents, or personal data.
