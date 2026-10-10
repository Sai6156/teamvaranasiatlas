"use client";

import { ArrowUpRight, FileText, Globe, ShieldCheck } from "lucide-react";
import type { Workspace } from "@/lib/client";

export const demoQuestions: Record<string, string[]> = {
  reliance: [
    "What were Reliance’s revenue and profit in FY 2024–25, and how did they change from the previous year?",
    "Which business segments contributed to Reliance’s FY 2024–25 performance?",
    "What does Reliance’s code of conduct say about conflicts of interest?",
  ],
  tcs: [
    "What were TCS’s revenue and profit in FY 2025–26? Include the comparison period and currency.",
    "What does TCS’s FY 2025–26 annual report say about AI and its business strategy?",
    "What sustainability initiatives and targets are reported by TCS?",
  ],
  infosys: [
    "What were Infosys’s revenue and net profit in FY 2024–25, and how did they change?",
    "What does Infosys’s annual report say about generative AI and Topaz?",
    "What employee training and sustainability initiatives does Infosys report?",
  ],
  wipro: [
    "What were Wipro’s revenue and profit in FY 2025–26? State the units and reporting period.",
    "What are Wipro’s strategic priorities in its FY 2025–26 annual report?",
    "What does Wipro’s code of conduct require when an employee faces a conflict of interest?",
  ],
  hcltech: [
    "What were HCLTech’s revenue and profit in FY 2025–26? Include the currency and prior-year comparison.",
    "What does HCLTech’s annual report say about AI and its business strategy?",
    "What does HCLTech’s code of conduct say about gifts and conflicts of interest?",
  ],
  microsoft: [
    "What were Microsoft’s revenue and operating income in fiscal 2025, and how did they change?",
    "How did Azure and Microsoft Cloud perform in fiscal 2025?",
    "What does Microsoft’s Trust Code say about raising concerns and retaliation?",
  ],
  apple: [
    "Compare Apple’s total net sales and net income across FY 2026 Q1, Q2 and Q3. Use each quarter separately, not year-to-date totals.",
    "What progress does Apple’s 2025 environmental report describe toward its 2030 carbon-neutral goal?",
    "What does Apple report about recycled materials and renewable energy? State the reporting year.",
  ],
  nvidia: [
    "What were NVIDIA’s revenue and net income in fiscal 2026? State the units and fiscal year end.",
    "What does NVIDIA’s fiscal 2026 annual report say about Data Center performance and AI demand?",
    "What responsibilities does NVIDIA’s finance team code set for financial reporting?",
  ],
  amazon: [
    "What were Amazon’s net sales and operating income in calendar 2025, and how did they change?",
    "How did AWS perform in 2025, and what growth drivers does Amazon discuss?",
    "What does Amazon’s code of business conduct say about conflicts of interest?",
  ],
  alphabet: [
    "What were Alphabet’s revenue and net income in Q1 2026, and what was the year-over-year growth?",
    "How did Google Cloud perform in Q1 2026?",
    "What does Google’s 2026 environmental report say about emissions, clean energy and data centers?",
  ],
};

export default function DemoLibrary({
  workspaces,
  onSelect,
  onCreate,
  onSignOut,
}: {
  workspaces: Workspace[];
  onSelect: (workspace: Workspace) => void;
  onCreate: () => void;
  onSignOut: () => void;
}) {
  const privateWorkspaces = workspaces.filter((w) => !w.is_demo);
  return (
    <div className="demo-library">
      <header className="demo-library-header">
        <span className="brand">
          <span className="brand-mark">
            <span />
            <span />
            <span />
          </span>
          atlas<span className="brand-dot">.</span>
        </span>
        <div>
          <button className="btn secondary small" onClick={onCreate}>
            Create private workspace
          </button>
          <button className="text-link" onClick={onSignOut}>
            Sign out
          </button>
        </div>
      </header>
      <main>
        <span className="eyebrow">EXPLORE THE COMPANY KNOWLEDGE LIBRARY</span>
        <h1>
          Ten companies.
          <br />
          Answers at your fingertips<span className="title-dot">.</span>
        </h1>
        <p className="demo-library-intro">
          Choose a company and ask across its public reports. Every source is
          already indexed, with citations you can open and verify.
        </p>
        <div className="demo-library-trust">
          <ShieldCheck size={17} />
          <span>
            Read-only public sources · Your conversations are private ·
            Historical reporting periods are labelled
          </span>
        </div>
        {privateWorkspaces.length > 0 && (
          <section className="demo-private-list">
            <h2>Your private workspaces</h2>
            <div>
              {privateWorkspaces.map((w) => (
                <button
                  key={w.id}
                  className="btn secondary"
                  onClick={() => onSelect(w)}
                >
                  {w.name}
                  <ArrowUpRight size={16} />
                </button>
              ))}
            </div>
          </section>
        )}
        {(["India", "Global"] as const).map((region) => (
          <section className="demo-company-section" key={region}>
            <div className="section-top">
              <h2>
                {region === "India" ? "Indian companies" : "Global companies"}
              </h2>
              <span className="muted-badge">
                <Globe size={13} />{" "}
                {
                  workspaces.filter(
                    (w) => w.is_demo && w.demo_region === region,
                  ).length
                }{" "}
                COMPANIES
              </span>
            </div>
            <div className="demo-company-grid">
              {workspaces
                .filter((w) => w.is_demo && w.demo_region === region)
                .map((w) => (
                  <button
                    className="demo-company-card"
                    key={w.id}
                    onClick={() => onSelect(w)}
                  >
                    <span className="demo-company-avatar">
                      {w.name.slice(0, 2).toUpperCase()}
                    </span>
                    <ArrowUpRight className="demo-company-arrow" size={20} />
                    <h3>{w.name}</h3>
                    <p>{demoQuestions[w.demo_slug || ""]?.[0]}</p>
                    <div>
                      <FileText size={14} />
                      <span>3 indexed source files</span>
                      <span className="demo-ready-dot" />
                      Ready to ask
                    </div>
                  </button>
                ))}
            </div>
          </section>
        ))}
        <p className="demo-library-footer">
          Sources are public company publications. Report parts preserve all
          original pages; financial periods may differ across documents.
        </p>
      </main>
    </div>
  );
}
