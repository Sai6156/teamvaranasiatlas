"use client";

import { useState } from "react";
import {
  ArrowUp,
  ArrowUpRight,
  BookOpen,
  Check,
  FileText,
  Sparkles,
} from "lucide-react";

const examples = [
  {
    label: "First day",
    question: "What should I do on my first day?",
    title: "Your first day, with a clear starting point.",
    answer:
      "Collect your laptop from IT, activate multifactor authentication and meet your buddy. Complete security training within five working days. [1]",
    file: "Example — Onboarding.docx",
    location: "Paragraph 1",
    passage:
      "On your first day, collect your laptop from IT, activate multifactor authentication, and meet your buddy. Complete security training within five working days.",
  },
  {
    label: "Travel",
    question: "When should I submit my travel expenses?",
    title: "The deadline is in your travel policy.",
    answer:
      "Submit your travel expense claims within 14 days of the trip. Keep your receipts and get manager approval before booking. [1]",
    file: "Example — Travel policy.pdf",
    location: "Page 1",
    passage:
      "Business travel requires manager approval before booking. Expenses are reimbursed up to INR 5000 per day with receipts. Submit travel expense claims within 14 days of the trip.",
  },
  {
    label: "Engineering",
    question: "What do I need before production access?",
    title: "Two requirements before you get access.",
    answer:
      "Activate multifactor authentication and get approval from your team lead before accessing production systems. [1]",
    file: "Example — Engineering guide.py",
    location: "Line 4",
    passage:
      "# Production access requires multifactor authentication and team lead approval.",
  },
];

export default function KnowledgePreview() {
  const [selected, setSelected] = useState(0);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const example = examples[selected];
  return (
    <>
      <div
        className="preview-example-tabs"
        role="group"
        aria-label="Try an illustrative question"
      >
        <span>Try a question</span>
        {examples.map((item, index) => (
          <button
            key={item.label}
            aria-pressed={selected === index}
            onClick={() => {
              setSelected(index);
              setEvidenceOpen(false);
            }}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="preview-query">
        <div className="mini-avatar">Y</div>
        <span>{example.question}</span>
      </div>
      <div className="preview-answer" key={selected}>
        <span className="ai-star">
          <Sparkles size={18} />
        </span>
        <div aria-live="polite">
          <strong>{example.title}</strong>
          <p>{example.answer}</p>
          <button
            className="preview-source"
            onClick={() => setEvidenceOpen((value) => !value)}
            aria-expanded={evidenceOpen}
            aria-label="Inspect example source"
          >
            <FileText size={17} />
            <span>
              {example.file}
              <small>{example.location}</small>
            </span>
            {evidenceOpen ? <Check size={15} /> : <ArrowUpRight size={15} />}
          </button>
          {evidenceOpen && (
            <div className="preview-evidence">
              <span>
                <BookOpen size={13} />
                Source passage
              </span>
              <p>{example.passage}</p>
              <small>
                Fictional starter data for this interactive preview.
              </small>
            </div>
          )}
        </div>
      </div>
      <div className="preview-input">
        <span>Ask a question. Follow the evidence.</span>
        <span>
          <ArrowUp size={17} />
        </span>
      </div>
    </>
  );
}
