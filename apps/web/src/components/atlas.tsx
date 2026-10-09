"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { Session } from "@supabase/supabase-js";
import {
  ArrowUp,
  ArrowUpRight,
  ArrowRight,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Command,
  Copy,
  Database,
  ExternalLink,
  FileCode2,
  FileSpreadsheet,
  FileText,
  Folder,
  FolderOpen,
  Globe,
  LayoutDashboard,
  LifeBuoy,
  Loader2,
  LockKeyhole,
  LogOut,
  Menu,
  MessageSquare,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  Square,
  Trash2,
  UploadCloud,
  Users,
  X,
  RotateCcw,
  Eye,
  EyeOff,
  Mail,
  Clock,
  Settings,
  AlertCircle,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ChatComposer from "./chat-composer";
import ChatHistory from "./chat-history";
import {
  api,
  apiBase,
  authHeaders,
  configured,
  supabase,
  type Workspace,
  type CompanyDocument,
  type Citation,
  type Message,
  type Conversation,
  type Member,
} from "@/lib/client";

const suggested = [
  {
    icon: Users,
    label: "People & policies",
    question: "What should a new employee know about our company policies?",
    color: "purple",
  },
  {
    icon: FileSpreadsheet,
    label: "Operations",
    question: "What are our expense and reimbursement guidelines?",
    color: "orange",
  },
  {
    icon: FileCode2,
    label: "Engineering",
    question: "How do we set up our development environment?",
    color: "blue",
  },
];
function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <span className="brand">
      <span className="brand-mark">
        <span />
        <span />
        <span />
      </span>
      {!compact && (
        <span>
          atlas<span className="brand-dot">.</span>
        </span>
      )}
    </span>
  );
}
function errorText(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
}
function size(bytes: number) {
  return bytes >= 1048576
    ? `${(bytes / 1048576).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}
function date(value: string) {
  return new Date(value).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
}
function FileIcon({ name }: { name: string }) {
  return /\.(csv|tsv|xlsx)$/i.test(name) ? (
    <FileSpreadsheet size={19} />
  ) : /\.(py|js|ts|tsx|json|sql|go|rs|java|css)$/i.test(name) ? (
    <FileCode2 size={19} />
  ) : (
    <FileText size={19} />
  );
}

export default function Atlas() {
  const pathname = usePathname();
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!configured) {
      setLoading(false);
      return;
    }
    const client = supabase();
    client.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });
    const { data } = client.auth.onAuthStateChange((event, next) => {
      setSession(next);
      setLoading(false);
      if (event === "PASSWORD_RECOVERY") {
        sessionStorage.setItem("atlas-recovery", "true");
        router.replace("/reset-password");
      }
    });
    return () => data.subscription.unsubscribe();
  }, [router]);
  useEffect(() => {
    if (!loading && !session && pathname.startsWith("/app"))
      router.replace("/login");
  }, [loading, session, pathname, router]);
  if (pathname === "/") return <Landing session={session} />;
  if (loading)
    return (
      <div className="loading-screen">
        <Logo />
        <Loader2 className="spin" />
        <p>Opening your secure workspace…</p>
      </div>
    );
  if (
    [
      "/login",
      "/signup",
      "/forgot-password",
      "/reset-password",
      "/auth/callback",
      "/join",
    ].includes(pathname)
  )
    return <AuthView path={pathname} session={session} />;
  if (pathname.startsWith("/app"))
    return session ? (
      <WorkspaceApp key={session.user.id} session={session} />
    ) : (
      <div className="loading-screen">
        <Loader2 className="spin" />
      </div>
    );
  return (
    <div className="loading-screen">
      <Logo />
      <h1>This page isn’t here.</h1>
      <Link className="btn primary" href="/">
        Back to Atlas
      </Link>
    </div>
  );
}

function Landing({ session }: { session: Session | null }) {
  return (
    <div className="landing">
      <nav className="landing-nav">
        <Link href="/" aria-label="Atlas home">
          <Logo />
        </Link>
        <div className="nav-links">
          <a href="#how-it-works">How it works</a>
          <a href="#security">Built for trust</a>
          <Link href="/login">Log in</Link>
          <Link
            className="btn primary small"
            href={session ? "/app" : "/signup"}
          >
            {session ? "Open workspace" : "Create your workspace"}
            <ArrowUpRight size={16} />
          </Link>
        </div>
      </nav>
      <main>
        <section className="hero">
          <div className="hero-copy">
            <span className="eyebrow">
              <span className="live-dot" /> KNOWLEDGE, WITHOUT THE SEARCH PARTY
            </span>
            <h1>
              Your company knows.
              <br />
              <span>Now everyone can.</span>
            </h1>
            <p>
              The policy in a PDF. The process in a doc. The answer buried in
              your code. Bring it together, ask a question, and get straight to
              the source.
            </p>
            <div className="hero-actions">
              <Link className="btn primary" href={session ? "/app" : "/signup"}>
                Find your next answer
                <ArrowRight size={18} />
              </Link>
              <a className="text-link" href="#how-it-works">
                See how it works
                <ChevronRight size={16} />
              </a>
            </div>
            <div className="hero-trust">
              <ShieldCheck size={15} />
              <span>Private workspaces</span>
              <span className="divider-dot">·</span>
              <span>Answers with evidence</span>
              <span className="divider-dot">·</span>
              <span>Your files, connected</span>
            </div>
          </div>
          <div className="hero-visual">
            <div className="visual-label">
              <span className="live-dot" /> A LITTLE LESS SEARCHING. A LOT MORE
              KNOWING.
            </div>
            <div className="preview-window">
              <div className="preview-top">
                <Logo />
                <span>
                  <LockKeyhole size={12} />
                  Workspace preview
                </span>
              </div>
              <div className="preview-query">
                <div className="mini-avatar">Y</div>
                <span>How do I get started on my first day?</span>
              </div>
              <div className="preview-answer">
                <span className="ai-star">
                  <Sparkles size={18} />
                </span>
                <div>
                  <strong>A great first day starts here.</strong>
                  <p>
                    Set up your accounts, meet your team, and check your
                    onboarding checklist. Atlas brings the relevant steps
                    together, with a source for every answer.
                  </p>
                  <div className="preview-source">
                    <FileText size={16} />
                    <span>
                      Onboarding handbook<span>Example source · Page 4</span>
                    </span>
                    <ArrowUpRight size={15} />
                  </div>
                </div>
              </div>
              <div className="preview-input">
                <span>Ask anything about your company…</span>
                <span>
                  <ArrowUp size={17} />
                </span>
              </div>
            </div>
            <div className="floating-file float-a">
              <span className="file-tile purple">
                <FileText size={19} />
              </span>
              <div>
                People handbook.pdf<small>People & culture</small>
              </div>
              <CheckCircle2 size={15} />
            </div>
            <div className="floating-file float-b">
              <span className="file-tile orange">
                <FileSpreadsheet size={19} />
              </span>
              <div>
                Operations.xlsx<small>Operations</small>
              </div>
              <CheckCircle2 size={15} />
            </div>
            <span className="visual-caption">
              Illustrative preview. Your answers come from your own files.
            </span>
          </div>
        </section>
        <div className="format-band">
          <span>ONE HOME FOR YOUR COMPANY KNOWLEDGE</span>
          <div>
            <FileText size={18} />
            PDF & documents
          </div>
          <div>
            <FileSpreadsheet size={18} />
            Spreadsheets
          </div>
          <div>
            <FileCode2 size={18} />
            Code & Markdown
          </div>
          <div>
            <BookOpen size={18} />
            Presentations & more
          </div>
        </div>
        <section className="how-section" id="how-it-works">
          <div className="section-heading">
            <span className="eyebrow">LESS FRICTION. MORE FLOW.</span>
            <h2>
              From scattered files
              <br />
              to shared understanding.
            </h2>
            <p>A familiar workspace. A much faster way to find what matters.</p>
          </div>
          <div className="feature-grid">
            <article>
              <span className="step-number">01</span>
              <UploadCloud />
              <h3>Bring your knowledge.</h3>
              <p>
                Upload policies, manuals, spreadsheets, and code. Organize them
                into collections your team understands.
              </p>
            </article>
            <article>
              <span className="step-number">02</span>
              <MessageSquare />
              <h3>Ask in your own words.</h3>
              <p>
                Get useful answers across your workspace, with the context to
                keep the conversation going.
              </p>
            </article>
            <article>
              <span className="step-number">03</span>
              <BookOpen />
              <h3>Follow the evidence.</h3>
              <p>
                Open the exact passage behind an answer. A page, a paragraph, a
                row, or a line of code.
              </p>
            </article>
          </div>
        </section>
        <section className="trust-section" id="security">
          <span className="trust-symbol">
            <ShieldCheck size={45} />
          </span>
          <div>
            <span className="eyebrow">
              COMPANY KNOWLEDGE DESERVES A PRIVATE HOME
            </span>
            <h2>Built around your boundaries.</h2>
            <p>
              Verified accounts, private file storage, organization-scoped
              access, and administrator-controlled uploads. Your team’s
              knowledge stays inside its workspace.
            </p>
          </div>
          <Link className="btn secondary" href="/signup">
            Create a secure workspace
            <ArrowRight size={17} />
          </Link>
        </section>
      </main>
      <footer className="landing-footer">
        <Logo />
        <span>Built by Team Varanasi · TriCity AI Hackathon</span>
        <span>Good answers start with good sources.</span>
      </footer>
    </div>
  );
}

function AuthView({
  path,
  session,
}: {
  path: string;
  session: Session | null;
}) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [invite, setInvite] = useState("");
  const [recovery, setRecovery] = useState(false);
  const signup = path === "/signup",
    forgot = path === "/forgot-password",
    reset = path === "/reset-password",
    join = path === "/join",
    callback = path === "/auth/callback";
  useEffect(() => {
    setError("");
    setNotice("");
    if (typeof window !== "undefined") {
      setInvite(
        new URLSearchParams(window.location.search).get("invite") ||
          sessionStorage.getItem("atlas-invite") ||
          "",
      );
      setRecovery(sessionStorage.getItem("atlas-recovery") === "true");
    }
  }, [path]);
  useEffect(() => {
    if (invite) sessionStorage.setItem("atlas-invite", invite);
  }, [invite]);
  useEffect(() => {
    if (session && !reset && !join && !callback)
      router.replace(sessionStorage.getItem("atlas-invite") ? "/join" : "/app");
    if (callback && session)
      router.replace(sessionStorage.getItem("atlas-invite") ? "/join" : "/app");
  }, [session, reset, join, callback, router]);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const client = supabase();
      if (join) {
        const result = await api<{ organization_id: string }>(
          "/invitations/accept",
          {
            method: "POST",
            body: JSON.stringify({ token: invite, full_name: name }),
          },
        );
        localStorage.setItem("atlas-workspace", result.organization_id);
        sessionStorage.removeItem("atlas-invite");
        router.replace("/app");
      } else if (forgot) {
        const { error } = await client.auth.resetPasswordForEmail(email, {
          redirectTo: window.location.origin + "/reset-password",
        });
        if (error) throw error;
        setNotice(
          "If an account exists for that email, a password reset link is on its way.",
        );
      } else if (reset) {
        if (!recovery || !session)
          throw new Error(
            "Open the password reset link from your email before setting a new password.",
          );
        const { error } = await client.auth.updateUser({ password });
        if (error) throw error;
        sessionStorage.removeItem("atlas-recovery");
        setNotice("Your password has been updated.");
        setPassword("");
        router.replace("/app");
      } else if (signup) {
        const { data, error } = await client.auth.signUp({
          email,
          password,
          options: {
            data: { full_name: name },
            emailRedirectTo: window.location.origin + "/auth/callback",
          },
        });
        if (error) throw error;
        setPassword("");
        if (data.session) router.replace("/app");
        else
          setNotice(
            "Check your inbox to verify your email. Then come back and sign in to create your workspace.",
          );
      } else {
        const { error } = await client.auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
        setPassword("");
        router.replace(
          sessionStorage.getItem("atlas-invite") ? "/join" : "/app",
        );
      }
    } catch (error) {
      setError(errorText(error));
    } finally {
      setBusy(false);
    }
  }
  async function resend() {
    setBusy(true);
    try {
      const { error } = await supabase().auth.resend({
        type: "signup",
        email,
        options: { emailRedirectTo: window.location.origin + "/auth/callback" },
      });
      if (error) throw error;
      setNotice("A new verification email has been sent.");
    } catch (error) {
      setError(errorText(error));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-layout">
      <aside className="auth-story">
        <Link href="/">
          <Logo />
        </Link>
        <div className="auth-story-copy">
          <span className="eyebrow">A LITTLE CLARITY GOES A LONG WAY</span>
          <h1>
            Your next answer
            <br />
            is already here.
          </h1>
          <p>
            Turn your company’s scattered knowledge into a place where everyone
            can find their way.
          </p>
          <div className="auth-testimonial">
            <BookOpen size={24} />
            <p>
              From “where’s that document?”
              <br />
              to “here’s what you need.”
            </p>
            <span>One workspace. Your whole company.</span>
          </div>
        </div>
        <span className="auth-story-footer">
          <ShieldCheck size={16} />
          Private by design. Grounded in your sources.
        </span>
      </aside>
      <main className="auth-main">
        <Link className="back-home" href="/">
          <ArrowRight size={15} />
          Back to home
        </Link>
        <div className="auth-form-wrap">
          <span className="auth-icon">
            {forgot ? <Mail /> : join ? <Users /> : <LockKeyhole />}
          </span>
          <span className="eyebrow">
            {signup
              ? "MAKE ROOM FOR BETTER ANSWERS"
              : "YOUR KNOWLEDGE, WITHIN REACH"}
          </span>
          <h2>
            {signup
              ? "Create your account"
              : forgot
                ? "Forgot your password?"
                : reset
                  ? "Set a new password"
                  : join
                    ? "Join your team"
                    : callback
                      ? "Confirming your account…"
                      : "Welcome back."}
          </h2>
          <p>
            {signup
              ? "Start with a secure account. Create or join a company workspace next."
              : forgot
                ? "We’ll send a secure link to help you get back in."
                : reset
                  ? "Choose a strong password for your account."
                  : join
                    ? "Accept your workspace invitation using the email it was sent to."
                    : callback
                      ? "We’re checking your email verification."
                      : "Sign in to pick up where you left off."}
          </p>
          {!configured && (
            <div className="notice warning">
              <AlertCircle size={17} />
              <span>
                Authentication setup is in progress. Signup opens when the
                secure backend is connected.
              </span>
            </div>
          )}
          {error && (
            <div className="notice error" role="alert">
              <AlertCircle size={17} />
              {error}
            </div>
          )}
          {notice && (
            <div className="notice success" role="status">
              <CheckCircle2 size={17} />
              {notice}
            </div>
          )}
          {callback ? (
            <div className="callback-actions">
              <Link className="btn primary" href="/login">
                Continue to sign in
                <ArrowRight size={16} />
              </Link>
            </div>
          ) : join && !session ? (
            <div>
              <p className="notice">
                Sign in with your invited email first. Your invitation will be
                saved.
              </p>
              <Link className="btn primary full" href="/login">
                Sign in to accept invitation
              </Link>
              <Link className="text-link" href="/signup">
                New here? Create an account
              </Link>
            </div>
          ) : (
            <form onSubmit={submit}>
              {(signup || join) && (
                <label>
                  Full name
                  <input
                    autoComplete="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Your full name"
                    required
                    maxLength={100}
                  />
                </label>
              )}
              {!reset && !join && (
                <label>
                  Work email
                  <input
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    required
                    maxLength={254}
                  />
                </label>
              )}
              {!forgot && !join && (
                <label>
                  <span className="label-row">
                    Password
                    {!signup && !reset && (
                      <Link href="/forgot-password">Forgot password?</Link>
                    )}
                  </span>
                  <span className="password-field">
                    <input
                      type={show ? "text" : "password"}
                      autoComplete={
                        signup || reset ? "new-password" : "current-password"
                      }
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder={
                        signup || reset
                          ? "At least 12 characters"
                          : "Enter your password"
                      }
                      required
                      minLength={signup || reset ? 12 : 1}
                      maxLength={128}
                    />
                    <button
                      type="button"
                      onClick={() => setShow(!show)}
                      aria-label={show ? "Hide password" : "Show password"}
                    >
                      {show ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </span>
                  {(signup || reset) && (
                    <small className="field-help">
                      Use a unique password with at least 12 characters.
                    </small>
                  )}
                </label>
              )}
              <button
                className="btn primary full"
                disabled={
                  busy ||
                  !configured ||
                  (join && !invite) ||
                  (reset && !recovery)
                }
              >
                {busy ? <Loader2 size={18} className="spin" /> : null}
                {signup
                  ? "Create account"
                  : forgot
                    ? "Send reset link"
                    : reset
                      ? "Update password"
                      : join
                        ? "Join workspace"
                        : "Sign in"}
                {!busy && <ArrowRight size={17} />}
              </button>
            </form>
          )}
          {notice && signup && email && (
            <button
              className="text-link resend"
              onClick={resend}
              disabled={busy}
            >
              Resend verification email
            </button>
          )}
          {!forgot && !reset && !join && !callback && (
            <div className="auth-switch">
              {signup ? "Already have an account?" : "New to Atlas?"}{" "}
              <Link href={signup ? "/login" : "/signup"}>
                {signup ? "Sign in" : "Create an account"}
              </Link>
            </div>
          )}
          {forgot && (
            <div className="auth-switch">
              <Link href="/login">Back to sign in</Link>
            </div>
          )}
          <div className="auth-privacy">
            <ShieldCheck size={14} />
            Your password is handled securely by Supabase Auth.
          </div>
        </div>
        <div className="auth-bottom">ATLAS · COMPANY KNOWLEDGE, CONNECTED</div>
      </main>
    </div>
  );
}

function WorkspaceApp({ session }: { session: Session }) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [view, setView] = useState("overview");
  const [documents, setDocuments] = useState<CompanyDocument[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [status, setStatus] = useState("");
  const [citation, setCitation] = useState<Citation | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [menu, setMenu] = useState(false);
  const [filter, setFilter] = useState("");
  const [collection, setCollection] = useState("");
  const [toast, setToast] = useState("");
  const [members, setMembers] = useState<Member[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [focusPrompt, setFocusPrompt] = useState(0);
  const [showLatest, setShowLatest] = useState(false);
  const abort = useRef<AbortController | null>(null);
  const chatOperation = useRef(0);
  const messagesViewport = useRef<HTMLDivElement>(null);
  const followLatest = useRef(true);
  const end = useRef<HTMLDivElement | null>(null);
  const currentWorkspace = useRef<string | null>(null);
  useEffect(() => {
    currentWorkspace.current = workspace?.id ?? null;
  }, [workspace]);
  const router = useRouter();
  const refreshDocuments = useCallback(async () => {
    if (workspace) {
      const rows = await api<CompanyDocument[]>(
        `/workspaces/${workspace.id}/documents`,
      );
      if (currentWorkspace.current === workspace.id) setDocuments(rows);
    }
  }, [workspace]);
  const refreshConversations = useCallback(async () => {
    if (workspace) {
      const rows = await api<Conversation[]>(
        `/workspaces/${workspace.id}/conversations`,
      );
      if (currentWorkspace.current === workspace.id) setConversations(rows);
    }
  }, [workspace]);
  useEffect(() => {
    api<Workspace[]>("/workspaces")
      .then((rows) => {
        setWorkspaces(rows);
        setWorkspace(
          rows.find((w) => w.id === localStorage.getItem("atlas-workspace")) ||
            rows[0] ||
            null,
        );
      })
      .catch((error) => setError(errorText(error)))
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    if (!workspace) return;
    localStorage.setItem("atlas-workspace", workspace.id);
    setMessages([]);
    setConversationId(null);
    setDocuments([]);
    setConversations([]);
    setCitation(null);
    setMembers([]);
    setCollection("");
    setFilter("");
    setError("");
    Promise.all([
      refreshDocuments(),
      refreshConversations(),
      api<Member[]>(`/workspaces/${workspace.id}/members`).then((rows) => {
        if (currentWorkspace.current === workspace.id) setMembers(rows);
      }),
    ]).catch((error) => setError(errorText(error)));
  }, [workspace, refreshDocuments, refreshConversations]);
  useEffect(() => {
    if (!workspace) return;
    const timer = setInterval(() => {
      if (
        documents.some(
          (d) => !["ready", "failed", "deleted"].includes(d.status),
        )
      )
        refreshDocuments().catch(() => {});
    }, 3000);
    return () => clearInterval(timer);
  }, [workspace, documents, refreshDocuments]);
  useEffect(() => {
    const viewport = messagesViewport.current;
    if (viewport && followLatest.current)
      viewport.scrollTop = viewport.scrollHeight;
  }, [messages, status]);
  useEffect(() => {
    function key(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setHistoryOpen(true);
      }
    }
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
  }, []);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 4000);
    return () => clearTimeout(timer);
  }, [toast]);
  useEffect(() => () => abort.current?.abort(), []);
  const ready = documents.filter((d) => d.status === "ready");
  const collections = [...new Set(documents.map((d) => d.collection))].sort();
  const fullName =
    session.user.user_metadata.full_name ||
    session.user.email?.split("@")[0] ||
    "there";
  function newChat() {
    chatOperation.current++;
    abort.current?.abort();
    setStreaming(false);
    setHistoryLoading(false);
    setStatus("");
    followLatest.current = true;
    setMessages([]);
    setConversationId(null);
    setQuestion("");
    setError("");
    setView("ask");
    setMenu(false);
  }
  async function loadConversation(id: string) {
    const operation = ++chatOperation.current;
    abort.current?.abort();
    setStreaming(false);
    setHistoryLoading(true);
    setView("ask");
    setMenu(false);
    setConversationId(id);
    setMessages([]);
    setQuestion("");
    setStatus("");
    followLatest.current = true;
    try {
      const loaded = await api<Message[]>(`/conversations/${id}/messages`);
      if (operation !== chatOperation.current) return;
      setMessages(loaded);
      setConversationId(id);
      setView("ask");
      setMenu(false);
    } catch (error) {
      if (operation === chatOperation.current) setError(errorText(error));
    } finally {
      if (operation === chatOperation.current) setHistoryLoading(false);
    }
  }
  async function ask(value = question) {
    if (!workspace || !value.trim() || streaming) return;
    setError("");
    setView("ask");
    setQuestion("");
    setStreaming(true);
    const operation = ++chatOperation.current;
    followLatest.current = true;
    setShowLatest(false);
    setStatus("Connecting to your knowledge");
    setCitation(null);
    setMessages((previous) => [
      ...previous,
      { role: "user", content: value },
      { role: "assistant", content: "", citations: [] },
    ]);
    const controller = new AbortController();
    abort.current = controller;
    let finished = false;
    try {
      const headers = await authHeaders();
      const response = await fetch(
        `${apiBase}/workspaces/${workspace.id}/chat`,
        {
          method: "POST",
          headers: { ...headers, "Content-Type": "application/json" },
          body: JSON.stringify({
            question: value,
            conversation_id: conversationId,
            collection: collection || null,
          }),
          signal: controller.signal,
        },
      );
      if (!response.ok) {
        const data = await response.json();
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Could not complete your question.",
        );
      }
      if (!response.body) throw new Error("Streaming is unavailable.");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value: chunk } = await reader.read();
        if (operation !== chatOperation.current) {
          await reader.cancel();
          return;
        }
        if (done) break;
        buffer += decoder.decode(chunk, { stream: true });
        let boundary;
        while ((boundary = buffer.indexOf("\n\n")) >= 0) {
          const block = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          if (!block.startsWith("data:")) continue;
          const data = JSON.parse(block.slice(5).trim());
          if (data.type === "conversation") setConversationId(data.id);
          if (data.type === "status") setStatus(data.text);
          if (data.type === "warning") setToast(data.text);
          if (data.type === "model")
            setMessages((previous) =>
              previous.map((m, i) =>
                i === previous.length - 1 ? { ...m, model: data.model } : m,
              ),
            );
          if (data.type === "token")
            setMessages((previous) =>
              previous.map((m, i) =>
                i === previous.length - 1
                  ? { ...m, content: m.content + data.text }
                  : m,
              ),
            );
          if (data.type === "reset")
            setMessages((previous) =>
              previous.map((m, i) =>
                i === previous.length - 1 ? { ...m, content: data.text } : m,
              ),
            );
          if (data.type === "done") {
            finished = true;
            setMessages((previous) =>
              previous.map((m, i) =>
                i === previous.length - 1
                  ? { ...m, citations: data.citations, model: data.model }
                  : m,
              ),
            );
          }
          if (data.type === "error") throw new Error(data.text);
        }
      }
      if (!finished)
        throw new Error(
          "The connection ended before this answer was complete. Please retry.",
        );
      await refreshConversations();
    } catch (error) {
      if (operation !== chatOperation.current) return;
      const message = controller.signal.aborted
        ? "Answer stopped. This partial response has not been verified."
        : errorText(error);
      setMessages((previous) =>
        previous.map((m, i) =>
          i === previous.length - 1 ? { ...m, error: message } : m,
        ),
      );
    } finally {
      if (operation === chatOperation.current) {
        setStreaming(false);
        setStatus("");
        abort.current = null;
      }
    }
  }
  async function signOut() {
    abort.current?.abort();
    await supabase().auth.signOut();
    localStorage.removeItem("atlas-workspace");
    router.replace("/login");
  }
  if (loading)
    return (
      <div className="loading-screen">
        <Logo />
        <Loader2 className="spin" />
        <p>Finding your workspaces…</p>
      </div>
    );
  if (!workspace)
    return (
      <Onboarding
        name={fullName}
        error={error}
        onCreated={(created) => {
          setWorkspaces([...workspaces, created]);
          setWorkspace(created);
          setError("");
        }}
        onSignOut={signOut}
        onBack={
          workspaces.length ? () => setWorkspace(workspaces[0]) : undefined
        }
      />
    );
  return (
    <div className="app-layout">
      {menu && (
        <button
          className="sidebar-scrim"
          onClick={() => setMenu(false)}
          aria-label="Close navigation"
        />
      )}
      <aside className={`sidebar ${menu ? "mobile-open" : ""}`}>
        <Link href="/" className="sidebar-logo">
          <Logo />
        </Link>
        <label className="workspace-switch">
          <span className="workspace-avatar">
            {workspace.name.slice(0, 1).toUpperCase()}
          </span>
          <select
            aria-label="Select workspace"
            value={workspace.id}
            disabled={streaming}
            onChange={(e) => {
              if (e.target.value === "__new") {
                setWorkspace(null);
                return;
              }
              setWorkspace(
                workspaces.find((w) => w.id === e.target.value) || workspace,
              );
              setView("overview");
            }}
          >
            {workspaces.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
            <option value="__new">+ Create new workspace</option>
          </select>
          <ChevronDown size={15} />
        </label>
        <span className="sidebar-caption">WORKSPACE</span>
        <nav className="app-nav">
          {[
            { id: "overview", label: "Overview", icon: LayoutDashboard },
            { id: "ask", label: "Ask Atlas", icon: Sparkles },
            { id: "documents", label: "Knowledge library", icon: FolderOpen },
            { id: "team", label: "Team & access", icon: Users },
          ].map((item) => (
            <button
              key={item.id}
              className={view === item.id ? "active" : ""}
              onClick={() => {
                setView(item.id);
                setMenu(false);
                setError("");
              }}
            >
              <item.icon size={18} />
              {item.label}
              {item.id === "documents" && (
                <span className="nav-count">{documents.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-section-heading">
          <span>RECENT CONVERSATIONS</span>
          <button title="New conversation" onClick={newChat}>
            <Plus size={16} />
          </button>
        </div>
        <button
          className="sidebar-history-search"
          onClick={() => setHistoryOpen(true)}
        >
          <Search size={15} />
          <span>Search all chats</span>
          <kbd>Ctrl K</kbd>
        </button>
        <div className="recent-conversations">
          {conversations.length ? (
            conversations.map((c) => (
              <button
                key={c.id}
                onClick={() => loadConversation(c.id)}
                className={conversationId === c.id ? "selected" : ""}
                title={c.title}
              >
                <MessageSquare size={14} />
                <span>{c.title}</span>
              </button>
            ))
          ) : (
            <p>
              Your conversations will
              <br />
              find a home here.
            </p>
          )}
        </div>
        {!!conversations.length && (
          <button
            className="all-chats-link"
            onClick={() => setHistoryOpen(true)}
          >
            View all conversations
            <ChevronRight size={13} />
          </button>
        )}
        <div className="sidebar-bottom">
          <div className="private-workspace">
            <ShieldCheck size={18} />
            <div>
              Private workspace<small>Only your team has access</small>
            </div>
          </div>
          <button className="profile" onClick={signOut} title="Sign out">
            <span className="profile-avatar">
              {fullName.slice(0, 2).toUpperCase()}
            </span>
            <span>
              {fullName}
              <small>
                {workspace.role === "admin" ? "Workspace admin" : "Team member"}
              </small>
              {doc.status === "extracting" && !!doc.total_pages && (
                <small>
                  Reading page {doc.processed_pages || 0} of {doc.total_pages}
                </small>
              )}
              {doc.status === "embedding" && !!doc.index_total_chunks && (
                <small>
                  Indexing {doc.index_completed_chunks || 0} of{" "}
                  {doc.index_total_chunks} passages
                </small>
              )}
            </span>
            <LogOut size={16} />
          </button>
        </div>
      </aside>
      <div className="app-main">
        <header className="app-header">
          <div>
            <button
              className="mobile-menu icon-button"
              onClick={() => setMenu(true)}
              aria-label="Open navigation"
            >
              <Menu size={20} />
            </button>
            <span className="breadcrumb">
              Workspace
              <ChevronRight size={13} />
              <strong>
                {view === "overview"
                  ? "Overview"
                  : view === "ask"
                    ? "Ask Atlas"
                    : view === "documents"
                      ? "Knowledge library"
                      : "Team & access"}
              </strong>
            </span>
          </div>
          <div className="header-actions">
            <span className="secure-badge">
              <LockKeyhole size={12} />
              Private & secure
            </span>
            {workspace.role === "admin" && (
              <button
                className="btn primary small"
                onClick={() => setUploadOpen(true)}
              >
                <Plus size={16} />
                Add knowledge
              </button>
            )}
          </div>
        </header>
        <main
          className={`workspace-content ${view === "ask" ? "chat-content" : ""}`}
        >
          {error && (
            <div className="notice error" role="alert">
              <AlertCircle size={17} />
              {error}
              <button
                className="icon-button"
                onClick={() => setError("")}
                aria-label="Dismiss error"
              >
                <X size={16} />
              </button>
            </div>
          )}
          {view === "overview" && (
            <>
              <div className="page-title">
                <span className="eyebrow">YOUR COMPANY, CONNECTED</span>
                <h1>
                  A little clarity, {fullName.split(" ")[0]}
                  <span className="title-dot">.</span>
                </h1>
                <p>Everything your team knows. One place to find it.</p>
              </div>
              <section className="ask-banner">
                <div className="banner-grid" />
                <span className="banner-star">
                  <Sparkles size={28} />
                </span>
                <div className="banner-copy">
                  <span>MAKE YOUR NEXT QUESTION A GOOD ONE</span>
                  <h2>What would you like to know?</h2>
                  <p>Ask across your documents. Get an answer you can trace.</p>
                </div>
                <form
                  className="banner-search"
                  onSubmit={(e) => {
                    e.preventDefault();
                    ask();
                  }}
                >
                  <Search size={19} />
                  <input
                    aria-label="Ask your company knowledge"
                    placeholder="Ask anything about your company…"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    maxLength={20000}
                  />
                  <button
                    type="submit"
                    aria-label="Ask Atlas"
                    disabled={!question.trim() || streaming}
                  >
                    <ArrowUp size={20} />
                  </button>
                </form>
                <span className="banner-foot">
                  <ShieldCheck size={12} />
                  Grounded in your workspace. Backed by sources.
                </span>
              </section>
              <div className="stats-grid">
                <Stat
                  icon={FileText}
                  label="Documents"
                  value={documents.length}
                  detail="In your knowledge library"
                />
                <Stat
                  icon={Database}
                  label="Ready to search"
                  value={ready.length}
                  detail={
                    documents.length === ready.length
                      ? "All documents are up to date"
                      : "Processing your latest knowledge"
                  }
                />
                <Stat
                  icon={Folder}
                  label="Collections"
                  value={collections.length}
                  detail="Organized around your team"
                />
                <Stat
                  icon={Users}
                  label="Team members"
                  value={members.length}
                  detail="Connected to this workspace"
                />
              </div>
              <section className="workspace-section">
                <div className="section-top">
                  <div>
                    <h2>A good place to start</h2>
                    <p>Try a question your documents can answer.</p>
                  </div>
                  <span className="muted-badge">MADE FOR YOUR EVERYDAY</span>
                </div>
                <div className="suggestion-grid">
                  {suggested.map((item) => (
                    <button
                      key={item.label}
                      className="suggestion-card"
                      onClick={() => ask(item.question)}
                      disabled={streaming}
                    >
                      <span className={`file-tile ${item.color}`}>
                        <item.icon size={19} />
                      </span>
                      <span className="suggestion-category">{item.label}</span>
                      <strong>{item.question}</strong>
                      <ArrowUpRight size={17} />
                    </button>
                  ))}
                </div>
              </section>
              <section className="workspace-section">
                <div className="section-top">
                  <div>
                    <h2>Recently added knowledge</h2>
                    <p>The latest pieces of your company’s story.</p>
                  </div>
                  <button
                    className="text-link"
                    onClick={() => setView("documents")}
                  >
                    View library
                    <ArrowRight size={15} />
                  </button>
                </div>
                {documents.length ? (
                  <DocumentTable
                    documents={documents.slice(0, 4)}
                    admin={workspace.role === "admin"}
                    onSource={async (doc) => {
                      try {
                        const source = await api<{ url: string }>(
                          `/documents/${doc.id}/source`,
                        );
                        window.open(
                          source.url,
                          "_blank",
                          "noopener,noreferrer",
                        );
                      } catch (error) {
                        setError(errorText(error));
                      }
                    }}
                    onDelete={async (doc) => {
                      if (
                        !window.confirm(
                          `Delete ${doc.name}? It will stop appearing in answers immediately.`,
                        )
                      )
                        return;
                      try {
                        await api(`/documents/${doc.id}`, { method: "DELETE" });
                        await refreshDocuments();
                        setToast("Document removed from your workspace.");
                      } catch (error) {
                        setError(errorText(error));
                      }
                    }}
                    onRetry={async (doc) => {
                      try {
                        await api(`/documents/${doc.id}/retry`, {
                          method: "POST",
                        });
                        await refreshDocuments();
                      } catch (error) {
                        setError(errorText(error));
                      }
                    }}
                  />
                ) : (
                  <EmptyLibrary
                    admin={workspace.role === "admin"}
                    onUpload={() => setUploadOpen(true)}
                    onSamples={async () => {
                      await api(
                        `/workspaces/${workspace.id}/starter-knowledge`,
                        { method: "POST" },
                      );
                      await refreshDocuments();
                      setToast(
                        "Example knowledge added. Atlas is indexing five fictional company files.",
                      );
                    }}
                  />
                )}
              </section>
            </>
          )}
          {view === "documents" && (
            <>
              <div className="page-title title-with-action">
                <div>
                  <span className="eyebrow">
                    THE FOUNDATION OF GOOD ANSWERS
                  </span>
                  <h1>
                    Knowledge library<span className="title-dot">.</span>
                  </h1>
                  <p>Organize your files. Keep your team in the know.</p>
                </div>
                {workspace.role === "admin" && (
                  <button
                    className="btn primary"
                    onClick={() => setUploadOpen(true)}
                  >
                    <UploadCloud size={18} />
                    Upload files
                  </button>
                )}
              </div>
              <div className="library-toolbar">
                <div className="search-field">
                  <Search size={17} />
                  <input
                    aria-label="Search files"
                    placeholder="Search files by name…"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                  />
                </div>
                <select
                  aria-label="Filter collection"
                  value={collection}
                  onChange={(e) => setCollection(e.target.value)}
                >
                  <option value="">All collections</option>
                  {collections.map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
                <span>{documents.length} documents</span>
                <button
                  className="icon-button"
                  onClick={() =>
                    refreshDocuments().catch((error) =>
                      setError(errorText(error)),
                    )
                  }
                  title="Refresh library"
                >
                  <RotateCcw size={16} />
                </button>
              </div>
              {documents.length ? (
                <DocumentTable
                  documents={documents.filter(
                    (d) =>
                      d.name.toLowerCase().includes(filter.toLowerCase()) &&
                      (!collection || d.collection === collection),
                  )}
                  admin={workspace.role === "admin"}
                  onSource={async (doc) => {
                    try {
                      const source = await api<{ url: string }>(
                        `/documents/${doc.id}/source`,
                      );
                      window.open(source.url, "_blank", "noopener,noreferrer");
                    } catch (error) {
                      setError(errorText(error));
                    }
                  }}
                  onDelete={async (doc) => {
                    if (
                      !window.confirm(
                        `Delete ${doc.name}? This permanently removes the file.`,
                      )
                    )
                      return;
                    try {
                      await api(`/documents/${doc.id}`, { method: "DELETE" });
                      await refreshDocuments();
                      setToast("Document removed.");
                    } catch (error) {
                      setError(errorText(error));
                    }
                  }}
                  onRetry={async (doc) => {
                    try {
                      await api(`/documents/${doc.id}/retry`, {
                        method: "POST",
                      });
                      await refreshDocuments();
                    } catch (error) {
                      setError(errorText(error));
                    }
                  }}
                />
              ) : (
                <EmptyLibrary
                  admin={workspace.role === "admin"}
                  onUpload={() => setUploadOpen(true)}
                  onSamples={async () => {
                    await api(`/workspaces/${workspace.id}/starter-knowledge`, {
                      method: "POST",
                    });
                    await refreshDocuments();
                    setToast(
                      "Example knowledge added. Atlas is indexing five fictional company files.",
                    );
                  }}
                />
              )}
              <div className="library-info">
                <ShieldCheck size={17} />
                <p>
                  Files are stored privately and only searched within this
                  workspace. Processing errors appear beside the file, with a
                  retry option for administrators.
                </p>
              </div>
            </>
          )}
          {view === "ask" && (
            <>
              <div className="chat-top">
                <div>
                  <Sparkles size={18} />
                  <strong>Ask Atlas</strong>
                  <span>Your company knowledge, in conversation.</span>
                </div>
                <button
                  className="btn secondary small"
                  onClick={newChat}
                  disabled={streaming}
                >
                  <Plus size={15} />
                  New conversation
                </button>
              </div>
              <div
                className="chat-messages"
                ref={messagesViewport}
                onScroll={() => {
                  const element = messagesViewport.current;
                  if (element) {
                    const nearBottom =
                      element.scrollHeight -
                        element.scrollTop -
                        element.clientHeight <
                      80;
                    followLatest.current = nearBottom;
                    setShowLatest(!nearBottom);
                  }
                }}
              >
                {historyLoading && (
                  <div className="history-loading">
                    <Loader2 className="spin" size={18} />
                    Opening conversation…
                  </div>
                )}
                {!messages.length && !historyLoading && (
                  <div className="chat-empty">
                    <span className="chat-empty-logo">
                      <Sparkles size={32} />
                    </span>
                    <span className="eyebrow">
                      A GOOD QUESTION CHANGES EVERYTHING
                    </span>
                    <h1>Let’s connect the dots.</h1>
                    <p>
                      Ask about a policy, a process, or a piece of code.
                      <br />
                      I’ll find the relevant knowledge and show my sources.
                    </p>
                    <div className="chat-suggestions">
                      {suggested.map((s) => (
                        <button key={s.label} onClick={() => ask(s.question)}>
                          <s.icon size={17} />
                          {s.question}
                          <ArrowUpRight size={15} />
                        </button>
                      ))}
                    </div>
                    {!ready.length && (
                      <div className="notice warning">
                        <AlertCircle size={16} />
                        Your workspace has no indexed documents yet. Add
                        knowledge to get sourced answers.
                      </div>
                    )}
                  </div>
                )}
                {messages.map((message, index) => (
                  <div className={`message ${message.role}`} key={index}>
                    <span
                      className={`message-avatar ${message.role === "assistant" ? "atlas-avatar" : ""}`}
                    >
                      {message.role === "assistant" ? (
                        <Sparkles size={17} />
                      ) : (
                        fullName.slice(0, 1).toUpperCase()
                      )}
                    </span>
                    <div className="message-body">
                      <div className="message-author">
                        {message.role === "assistant"
                          ? "Atlas"
                          : fullName.split(" ")[0]}
                        {message.role === "assistant" && (
                          <span>Knowledge assistant</span>
                        )}
                      </div>
                      {message.content ? (
                        <div className="markdown">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              a: ({ children, href }) => (
                                <a
                                  href={href}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                >
                                  {children}
                                </a>
                              ),
                            }}
                          >
                            {message.content}
                          </ReactMarkdown>
                        </div>
                      ) : streaming && index === messages.length - 1 ? (
                        <div className="thinking">
                          <span />
                          <span />
                          <span />
                          {status}
                        </div>
                      ) : null}
                      {message.error && (
                        <div className="notice error">
                          <AlertCircle size={16} />
                          {message.error}
                        </div>
                      )}
                      {!!message.citations?.length && (
                        <div className="answer-sources">
                          <span className="source-heading">
                            <BookOpen size={13} />
                            SOURCES · {message.citations.length}
                          </span>
                          <div>
                            {message.citations.map((c) => (
                              <button key={c.id} onClick={() => setCitation(c)}>
                                <span className="citation-number">
                                  {c.number}
                                </span>
                                <FileIcon name={c.document_name} />
                                <span>
                                  {c.document_name}
                                  <small>{c.location.label}</small>
                                </span>
                                <ArrowUpRight size={14} />
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                      {message.role === "user" && (
                        <div className="answer-actions">
                          <button
                            onClick={() =>
                              navigator.clipboard
                                .writeText(message.content)
                                .then(() => setToast("Prompt copied."))
                                .catch(() =>
                                  setToast("Select the prompt to copy it."),
                                )
                            }
                          >
                            <Copy size={13} />
                            Copy prompt
                          </button>
                          <button
                            onClick={() => {
                              setQuestion(message.content);
                              setFocusPrompt((value) => value + 1);
                            }}
                          >
                            <Settings size={13} />
                            Edit & resend
                          </button>
                        </div>
                      )}
                      {message.role === "assistant" &&
                        message.content &&
                        !(streaming && index === messages.length - 1) && (
                          <div className="answer-actions">
                            <button
                              onClick={() =>
                                navigator.clipboard
                                  .writeText(message.content)
                                  .then(() => setToast("Answer copied."))
                                  .catch(() =>
                                    setToast(
                                      "Copy is unavailable in this browser.",
                                    ),
                                  )
                              }
                            >
                              <Copy size={13} />
                              Copy answer
                            </button>
                            {message.citations?.length ? (
                              <span>
                                <CheckCircle2 size={12} />
                                Sources linked
                              </span>
                            ) : null}
                          </div>
                        )}
                    </div>
                  </div>
                ))}
                <div ref={end} />
              </div>
              {showLatest && (
                <button
                  className="jump-latest"
                  onClick={() => {
                    const element = messagesViewport.current;
                    if (element) {
                      followLatest.current = true;
                      element.scrollTo({
                        top: element.scrollHeight,
                        behavior: "smooth",
                      });
                      setShowLatest(false);
                    }
                  }}
                >
                  <ArrowUp size={14} />
                  Jump to latest
                </button>
              )}
              <div className="chat-composer-wrap">
                <div className="composer-scope">
                  <Folder size={13} />
                  <select
                    aria-label="Search scope"
                    value={collection}
                    onChange={(e) => setCollection(e.target.value)}
                    disabled={streaming}
                  >
                    <option value="">All knowledge</option>
                    {collections.map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </select>
                  <span>{ready.length} ready documents</span>
                </div>
                <ChatComposer
                  value={question}
                  onChange={setQuestion}
                  onSend={() => {
                    void ask();
                  }}
                  busy={streaming}
                  onStop={() => abort.current?.abort()}
                  onNotice={setToast}
                  focusSignal={focusPrompt}
                />
                <div className="composer-note">
                  <ShieldCheck size={12} />
                  Answers are based on your files. Check the evidence for
                  important decisions.
                  <span>Enter to send · Shift + Enter for a new line</span>
                </div>
              </div>
            </>
          )}
          {view === "team" && (
            <TeamView
              workspace={workspace}
              members={members}
              setToast={setToast}
              onMembersChanged={async () =>
                setMembers(
                  await api<Member[]>(`/workspaces/${workspace.id}/members`),
                )
              }
            />
          )}
        </main>
        <footer className="workspace-footer">
          <span>
            <span className="live-dot" />
            YOUR KNOWLEDGE, CONNECTED
          </span>
          <span>Built with care by Team Varanasi</span>
        </footer>
      </div>
      {toast && (
        <div className="toast" role="status">
          <CheckCircle2 size={17} />
          {toast}
        </div>
      )}
      {historyOpen && (
        <ChatHistory
          workspaceId={workspace.id}
          selected={conversationId}
          onSelect={(id) => {
            void loadConversation(id);
          }}
          onClose={() => setHistoryOpen(false)}
        />
      )}
      {uploadOpen && (
        <UploadModal
          workspace={workspace}
          collections={collections}
          onClose={() => setUploadOpen(false)}
          onUploaded={() => {
            refreshDocuments().catch((error) => setError(errorText(error)));
            setToast("Upload received. Atlas is preparing your knowledge.");
          }}
        />
      )}
      {citation && (
        <SourceDrawer citation={citation} onClose={() => setCitation(null)} />
      )}
    </div>
  );
}

function Stat({
  icon: Icon,
  label,
  value,
  detail,
}: {
  icon: typeof FileText;
  label: string;
  value: number;
  detail: string;
}) {
  return (
    <div className="stat-card">
      <div>
        <span>{label}</span>
        <Icon size={17} />
      </div>
      <strong>{value.toString().padStart(2, "0")}</strong>
      <small>{detail}</small>
    </div>
  );
}
function Onboarding({
  name,
  error,
  onCreated,
  onSignOut,
  onBack,
}: {
  name: string;
  error: string;
  onCreated: (workspace: Workspace) => void;
  onSignOut: () => void;
  onBack?: () => void;
}) {
  const [workspaceName, setWorkspaceName] = useState("");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");
  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setFailure("");
    try {
      onCreated(
        await api<Workspace>("/workspaces", {
          method: "POST",
          body: JSON.stringify({ name: workspaceName.trim(), full_name: name }),
        }),
      );
    } catch (error) {
      setFailure(errorText(error));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="onboarding">
      <header>
        <Link href="/">
          <Logo />
        </Link>
        <button className="text-link" onClick={onSignOut}>
          Sign out
          <LogOut size={16} />
        </button>
      </header>
      <main>
        {onBack && (
          <button className="text-link" onClick={onBack}>
            Back to your workspace
          </button>
        )}
        <span className="onboarding-icon">
          <FolderOpen size={33} />
        </span>
        <span className="eyebrow">LET’S MAKE IT YOURS</span>
        <h1>
          A home for your
          <br />
          company’s knowledge.
        </h1>
        <p>
          Welcome, {name.split(" ")[0]}. Create a private workspace to bring
          your documents and your team together.
        </p>
        {(error || failure) && (
          <div className="notice error">
            <AlertCircle size={16} />
            {failure || error}
          </div>
        )}
        <form onSubmit={create}>
          <label>
            Company or workspace name
            <input
              placeholder="e.g. Acme Operations"
              value={workspaceName}
              onChange={(e) => setWorkspaceName(e.target.value)}
              minLength={2}
              maxLength={100}
              required
              autoFocus
            />
          </label>
          <button className="btn primary full" disabled={busy}>
            {busy ? <Loader2 className="spin" size={17} /> : null}Create
            workspace
            <ArrowRight size={17} />
          </button>
        </form>
        <div className="onboarding-steps">
          <span>
            <CheckCircle2 />
            Secure account
          </span>
          <span className="current">
            <Folder />
            Create workspace
          </span>
          <span>
            <UploadCloud />
            Add knowledge
          </span>
        </div>
        <p className="field-help">
          Joining an existing team? Open the invitation link from your workspace
          administrator.
        </p>
      </main>
    </div>
  );
}
function EmptyLibrary({
  admin,
  onUpload,
  onSamples,
}: {
  admin: boolean;
  onUpload: () => void;
  onSamples?: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function loadExamples() {
    setBusy(true);
    setError("");
    try {
      await onSamples?.();
    } catch (error) {
      setError(errorText(error));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="empty-library">
      <div className="empty-file-stack">
        <FileText size={30} />
      </div>
      <h3>Your knowledge starts here.</h3>
      <p>
        {admin
          ? "Add your first document and turn what your company knows into answers your team can use."
          : "Your administrator can add documents so your team can start finding answers."}
      </p>
      {admin && (
        <button className="btn secondary small" onClick={onUpload}>
          <Plus size={16} />
          Add your first document
        </button>
      )}
      {admin && onSamples && (
        <div className="sample-quickstart">
          <button className="text-link" onClick={loadExamples} disabled={busy}>
            {busy ? (
              <Loader2 size={14} className="spin" />
            ) : (
              <Sparkles size={14} />
            )}
            Or explore with example knowledge
          </button>
          <small>
            Five fictional files. Real indexing and sourced answers.
          </small>
        </div>
      )}
      {error && (
        <div className="notice error" role="alert">
          {error}
        </div>
      )}
    </div>
  );
}
function DocumentTable({
  documents,
  admin,
  onSource,
  onDelete,
  onRetry,
}: {
  documents: CompanyDocument[];
  admin: boolean;
  onSource: (document: CompanyDocument) => void;
  onDelete: (document: CompanyDocument) => void;
  onRetry: (document: CompanyDocument) => void;
}) {
  return (
    <div className="document-table">
      <div className="table-heading">
        <span>DOCUMENT</span>
        <span>COLLECTION</span>
        <span>STATUS</span>
        <span>ADDED</span>
        <span />
      </div>
      {documents.map((doc) => (
        <div className="document-row" key={doc.id}>
          <button className="document-name" onClick={() => onSource(doc)}>
            <span
              className={`file-tile ${/\.(csv|xlsx)/i.test(doc.name) ? "orange" : /\.(ts|py|js)/i.test(doc.name) ? "blue" : "purple"}`}
            >
              <FileIcon name={doc.name} />
            </span>
            <span>
              <strong>{doc.name}</strong>
              <small>
                {size(doc.size_bytes)}
                {doc.chunk_count > 0 ? ` · ${doc.chunk_count} passages` : ""}
              </small>
              {doc.error_message && (
                <small className="file-error">{doc.error_message}</small>
              )}
              {doc.extraction_note && <small>{doc.extraction_note}</small>}
            </span>
          </button>
          <span className="collection-pill">
            <Folder size={12} />
            {doc.collection}
          </span>
          <span
            className={`status-pill ${doc.status}`}
            title={doc.error_message}
          >
            {doc.status === "ready" ? (
              <Check size={12} />
            ) : doc.status === "failed" ? (
              <AlertCircle size={12} />
            ) : (
              <Loader2 size={12} className="spin" />
            )}
            {doc.status === "ready"
              ? "Ready"
              : doc.status === "failed"
                ? "Needs attention"
                : doc.status === "uploaded"
                  ? "Awaiting processing"
                  : doc.status.charAt(0).toUpperCase() + doc.status.slice(1)}
          </span>
          <span className="document-date">{date(doc.created_at)}</span>
          <div className="document-actions">
            {doc.status === "failed" && admin && (
              <button title="Retry processing" onClick={() => onRetry(doc)}>
                <RotateCcw size={15} />
              </button>
            )}
            <button title="Open original" onClick={() => onSource(doc)}>
              <ExternalLink size={15} />
            </button>
            {admin && (
              <button title="Delete document" onClick={() => onDelete(doc)}>
                <Trash2 size={15} />
              </button>
            )}
          </div>
        </div>
      ))}
      {!documents.length && (
        <div className="no-results">No documents match your filters.</div>
      )}
    </div>
  );
}

function UploadModal({
  workspace,
  collections,
  onClose,
  onUploaded,
}: {
  workspace: Workspace;
  collections: string[];
  onClose: () => void;
  onUploaded: () => void;
}) {
  const [files, setFiles] = useState<File[]>([]);
  const [folder, setFolder] = useState("General");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");
  const [drag, setDrag] = useState(false);
  const input = useRef<HTMLInputElement | null>(null);
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !busy) onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [busy, onClose]);
  function select(incoming: File[]) {
    setError("");
    if (incoming.some((f) => f.size > 25 * 1024 * 1024)) {
      setError("Each file must be 25 MB or smaller.");
      return;
    }
    if (files.length + incoming.length > 10) {
      setError("Upload up to 10 files at a time.");
      return;
    }
    setFiles((previous) => [...previous, ...incoming]);
  }
  async function upload() {
    setBusy(true);
    setError("");
    let succeeded = 0;
    try {
      for (let i = 0; i < files.length; i++) {
        setProgress(`Uploading ${i + 1} of ${files.length} · ${files[i].name}`);
        const data = new FormData();
        data.append("file", files[i]);
        data.append("collection", folder.trim() || "General");
        await api(`/workspaces/${workspace.id}/documents`, {
          method: "POST",
          body: data,
        });
        succeeded++;
      }
      onUploaded();
      onClose();
    } catch (error) {
      setFiles((previous) => previous.slice(succeeded));
      setError(errorText(error));
      if (succeeded) onUploaded();
    } finally {
      setBusy(false);
      setProgress("");
    }
  }
  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget && !busy) onClose();
      }}
    >
      <section
        className="upload-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-title"
      >
        <div className="modal-top">
          <span className="file-tile green">
            <UploadCloud size={23} />
          </span>
          <button
            className="icon-button"
            onClick={onClose}
            disabled={busy}
            aria-label="Close upload"
          >
            <X size={21} />
          </button>
        </div>
        <h2 id="upload-title">Bring your knowledge.</h2>
        <p>Add the documents your team should be able to find.</p>
        <div
          className={`drop-zone ${drag ? "dragging" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            if (!busy) select(Array.from(e.dataTransfer.files));
          }}
        >
          <UploadCloud size={31} />
          <strong>Drop your files here</strong>
          <span>
            or{" "}
            <button
              className="text-link"
              onClick={() => input.current?.click()}
              disabled={busy}
            >
              browse files
            </button>
          </span>
          <small>
            PDF, DOCX, CSV, XLSX, PPTX, text, code & images · 25 MB each
          </small>
          <input
            ref={input}
            type="file"
            multiple
            className="hidden-input"
            onChange={(e) => {
              select(Array.from(e.target.files || []));
              e.target.value = "";
            }}
            disabled={busy}
          />
        </div>
        {!!files.length && (
          <div className="upload-file-list">
            {files.map((file, i) => (
              <div key={`${file.name}-${i}`}>
                <FileIcon name={file.name} />
                <span>
                  {file.name}
                  <small>{size(file.size)}</small>
                </span>
                <button
                  className="icon-button"
                  disabled={busy}
                  aria-label={`Remove ${file.name}`}
                  onClick={() =>
                    setFiles((previous) =>
                      previous.filter((_, index) => index !== i),
                    )
                  }
                >
                  <X size={15} />
                </button>
              </div>
            ))}
          </div>
        )}
        <label>
          Collection
          <input
            list="collection-options"
            value={folder}
            onChange={(e) => setFolder(e.target.value)}
            placeholder="e.g. People & policies"
            maxLength={80}
            disabled={busy}
          />
          <datalist id="collection-options">
            {["General", ...collections.filter((c) => c !== "General")].map(
              (c) => (
                <option key={c} value={c} />
              ),
            )}
          </datalist>
        </label>
        {error && (
          <div className="notice error" role="alert">
            <AlertCircle size={16} />
            {error}
          </div>
        )}
        {progress && (
          <p className="upload-progress" role="status">
            <Loader2 size={16} className="spin" />
            {progress}
          </p>
        )}
        <div className="upload-security">
          <LockKeyhole size={14} />
          Only members of {workspace.name} can access these files.
        </div>
        <div className="modal-actions">
          <button className="btn secondary" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button
            className="btn primary"
            onClick={upload}
            disabled={!files.length || busy}
          >
            {busy ? (
              <Loader2 className="spin" size={16} />
            ) : (
              <UploadCloud size={16} />
            )}
            Upload{" "}
            {files.length
              ? `${files.length} ${files.length === 1 ? "file" : "files"}`
              : "files"}
          </button>
        </div>
      </section>
    </div>
  );
}
function SourceDrawer({
  citation,
  onClose,
}: {
  citation: Citation;
  onClose: () => void;
}) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function open() {
    setBusy(true);
    setError("");
    try {
      const source = await api<{ url: string }>(
        `/documents/${citation.document_id}/source`,
      );
      window.open(source.url, "_blank", "noopener,noreferrer");
    } catch (error) {
      setError(errorText(error));
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    function key(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
  }, [onClose]);
  return (
    <div
      className="drawer-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <aside
        className="source-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-title"
      >
        <div className="drawer-heading">
          <span>
            <BookOpen size={17} />
            THE EVIDENCE
          </span>
          <button
            className="icon-button"
            onClick={onClose}
            aria-label="Close source"
          >
            <X size={20} />
          </button>
        </div>
        <div className="source-document">
          <span className="file-tile purple">
            <FileIcon name={citation.document_name} />
          </span>
          <div>
            <h2 id="source-title">{citation.document_name}</h2>
            <p>
              {citation.collection} · {citation.location.label}
            </p>
          </div>
        </div>
        <span className="source-context-label">
          PASSAGE USED IN THIS ANSWER
        </span>
        <div className="source-passage">
          <span className="citation-number">{citation.number}</span>
          <pre>{citation.content}</pre>
        </div>
        {error && <div className="notice error">{error}</div>}
        <button className="btn primary full" onClick={open} disabled={busy}>
          {busy ? (
            <Loader2 className="spin" size={16} />
          ) : (
            <ExternalLink size={16} />
          )}
          Open original document
        </button>
        <p className="source-note">
          <ShieldCheck size={14} />
          Access is checked again before opening the original. Download links
          expire after two minutes.
        </p>
      </aside>
    </div>
  );
}
function TeamView({
  workspace,
  members,
  setToast,
  onMembersChanged,
}: {
  workspace: Workspace;
  members: Member[];
  setToast: (message: string) => void;
  onMembersChanged: () => Promise<void>;
}) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("employee");
  const [busy, setBusy] = useState(false);
  const [link, setLink] = useState("");
  const [error, setError] = useState("");
  async function changeMember(member: Member, newRole: string | null) {
    if (
      !window.confirm(
        newRole
          ? `Change ${member.email} to ${newRole}?`
          : `Remove ${member.email} from this workspace?`,
      )
    )
      return;
    setError("");
    try {
      await api(`/workspaces/${workspace.id}/members/${member.user_id}`, {
        method: "POST",
        body: JSON.stringify({ role: newRole }),
      });
      await onMembersChanged();
      setToast("Workspace access updated.");
    } catch (error) {
      setError(errorText(error));
    }
  }
  const [activity, setActivity] = useState<
    { id: number; action: string; created_at: string }[]
  >([]);
  useEffect(() => {
    if (workspace.role === "admin")
      api<{ id: number; action: string; created_at: string }[]>(
        `/workspaces/${workspace.id}/activity`,
      )
        .then(setActivity)
        .catch(() => {});
  }, [workspace]);
  async function invite(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await api<{ url: string }>(
        `/workspaces/${workspace.id}/invitations`,
        { method: "POST", body: JSON.stringify({ email, role }) },
      );
      setLink(data.url);
    } catch (error) {
      setError(errorText(error));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-title">
        <span className="eyebrow">GOOD KNOWLEDGE IS SHARED KNOWLEDGE</span>
        <h1>
          Your team, connected<span className="title-dot">.</span>
        </h1>
        <p>People, permissions, and a private space to work together.</p>
      </div>
      <div className="team-grid">
        <section className="team-panel">
          <div className="section-top">
            <h2>Workspace members</h2>
            <span className="muted-badge">{members.length} MEMBERS</span>
          </div>
          {members.map((member) => (
            <div className="member-row" key={member.user_id}>
              <span className="profile-avatar">
                {(member.display_name || member.email)
                  .slice(0, 2)
                  .toUpperCase()}
              </span>
              <div>
                <strong>
                  {member.display_name || member.email.split("@")[0]}
                </strong>
                <span>{member.email}</span>
              </div>
              <span className={`role-pill ${member.role}`}>
                {member.role === "admin" ? "Admin" : "Employee"}
              </span>
              {workspace.role === "admin" && (
                <div className="member-controls">
                  <button
                    className="icon-button"
                    title={
                      member.role === "admin" ? "Make employee" : "Make admin"
                    }
                    onClick={() =>
                      changeMember(
                        member,
                        member.role === "admin" ? "employee" : "admin",
                      )
                    }
                  >
                    <Settings size={14} />
                  </button>
                  <button
                    className="icon-button"
                    title="Remove member"
                    onClick={() => changeMember(member, null)}
                  >
                    <X size={14} />
                  </button>
                </div>
              )}
            </div>
          ))}
          <div className="role-explainer">
            <ShieldCheck size={18} />
            <div>
              <strong>Access that makes sense.</strong>
              <p>
                Admins manage files and invitations. Employees search and read
                knowledge within this workspace. Conversations are private to
                their owner.
              </p>
            </div>
          </div>
        </section>
        <section className="team-panel invite-panel">
          <span className="file-tile green">
            <Users size={21} />
          </span>
          <h2>Make room for your team.</h2>
          <p>
            {workspace.role === "admin"
              ? "Create an invitation link for a specific email. Share it directly with your teammate."
              : "Your workspace admin can invite new people to join."}
          </p>
          {workspace.role === "admin" && (
            <form onSubmit={invite}>
              <label>
                Teammate’s email
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="teammate@company.com"
                />
              </label>
              <label>
                Workspace role
                <select value={role} onChange={(e) => setRole(e.target.value)}>
                  <option value="employee">Employee · search and read</option>
                  <option value="admin">
                    Admin · manage files and invitations
                  </option>
                </select>
              </label>
              <button className="btn primary full" disabled={busy}>
                {busy ? (
                  <Loader2 className="spin" size={16} />
                ) : (
                  <Plus size={16} />
                )}
                Create invitation
              </button>
            </form>
          )}
          {error && <div className="notice error">{error}</div>}
          {link && (
            <div className="invite-result">
              <span>
                <CheckCircle2 size={15} />
                Invitation ready · expires in 7 days
              </span>
              <p>Only the invited, verified email can accept this link.</p>
              <div>
                <input aria-label="Invitation link" readOnly value={link} />
                <button
                  className="icon-button"
                  onClick={() =>
                    navigator.clipboard
                      .writeText(link)
                      .then(() => setToast("Invitation link copied."))
                      .catch(() =>
                        setError("Select and copy the link manually."),
                      )
                  }
                  title="Copy invitation"
                >
                  <Copy size={16} />
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
      {workspace.role === "admin" && (
        <section className="workspace-section activity-panel">
          <div className="section-top">
            <div>
              <h2>Workspace activity</h2>
              <p>A record of important changes.</p>
            </div>
            <Clock size={18} />
          </div>
          {activity.length ? (
            activity.map((event) => (
              <div className="activity-row" key={event.id}>
                <span className="activity-dot" />
                <span>
                  {event.action.replaceAll(".", " ").replaceAll("_", " ")}
                </span>
                <time>{date(event.created_at)}</time>
              </div>
            ))
          ) : (
            <p className="field-help">Workspace changes will appear here.</p>
          )}
        </section>
      )}
    </>
  );
}
