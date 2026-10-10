"use client";

import { useEffect, useState } from "react";
import { ArrowUpRight, ChevronDown, Globe, RotateCcw } from "lucide-react";
import type { Workspace } from "@/lib/client";
import { demoQuestions } from "./demo-library";

const additionalQuestions: Record<string, string[]> = {
  reliance: [
    "Compare Reliance’s FY 2024–25 capital expenditure with FY 2023–24. State the units and cite the reported figures.",
    "How did Reliance’s Retail and Digital Services businesses perform in FY 2024–25? Keep their revenue and EBITDA separate.",
  ],
  tcs: [
    "Compare TCS’s consolidated revenue and net profit in FY 2025–26 and FY 2024–25. Calculate the growth rates and cite the inputs.",
    "What does TCS report about workforce size, voluntary attrition and employee development in FY 2025–26?",
  ],
  infosys: [
    "What were Infosys’s free cash flow and net profit in FY 2024–25? Calculate free cash flow conversion and state the accounting basis.",
    "Explain Infosys’s carbon-neutrality claim. Distinguish emissions reductions from offsets and identify the reporting year.",
  ],
  wipro: [
    "Compare Wipro’s FY 2025–26 revenue and profit with the preceding year. Distinguish consolidated results from IT Services margins.",
    "A Wipro employee’s relative owns a potential supplier that offers gifts. What disclosures and actions does the Code of Conduct require?",
  ],
  hcltech: [
    "For FY 2025–26, separate HCLTech’s revenue from services and hardware/software. Calculate each share of consolidated revenue.",
    "A supplier requests confidential pricing information during contract negotiations. What does HCLTech’s Code of Conduct require?",
  ],
  microsoft: [
    "Compare fiscal 2025 revenue and operating income across Microsoft’s three business segments. Calculate their operating margins.",
    "How does Azure revenue differ from Microsoft Cloud and Intelligent Cloud segment revenue in fiscal 2025? Cite the definitions and figures.",
  ],
  apple: [
    "Calculate Apple’s net profit margin for each of FY 2026 Q1, Q2 and Q3 using only that quarter’s three-month figures.",
    "Using Apple’s 2025 environmental report, distinguish its emissions baseline, achieved reduction, 2030 target and use of carbon removals.",
  ],
  nvidia: [
    "Compare NVIDIA’s fiscal 2026 and fiscal 2025 consolidated revenue, net income and net profit margin. Cite the inputs.",
    "What financial effects of H20 export restrictions does NVIDIA disclose for fiscal 2026? Separate recognized charges from future risks.",
  ],
  amazon: [
    "Compare Amazon’s 2025 North America, International and AWS operating margins using each segment’s sales and operating income.",
    "Why did Amazon’s 2025 free cash flow fall while operating income rose? Use the reported cash flow and investment figures.",
  ],
  alphabet: [
    "Why did Alphabet’s Q1 2026 net income grow differently from operating income? Explain the disclosed contribution from other income.",
    "Using Google’s 2026 environmental report, distinguish absolute emissions, emissions intensity, clean-energy matching and water replenishment.",
  ],
};

function chooseQuestions(slug: string): string[] {
  const pool = [
    ...(demoQuestions[slug] || []),
    ...(additionalQuestions[slug] || []),
  ];
  // Curated suggestions are shuffled locally; no model calls or prompt tokens.
  for (let index = pool.length - 1; index > 0; index--) {
    const other = Math.floor(Math.random() * (index + 1));
    [pool[index], pool[other]] = [pool[other], pool[index]];
  }
  return pool.slice(0, 4);
}

export default function DemoChatPicker({
  companies,
  selected,
  disabled,
  onSelect,
  onQuestion,
}: {
  companies: Workspace[];
  selected: Workspace | null;
  disabled: boolean;
  onSelect: (id: string) => void;
  onQuestion: (question: string) => void;
}) {
  const [questions, setQuestions] = useState<string[]>([]);
  const [expanded, setExpanded] = useState(true);
  useEffect(() => {
    setQuestions(selected ? chooseQuestions(selected.demo_slug || "") : []);
    setExpanded(true);
  }, [selected?.id, selected?.demo_slug]);
  if (!companies.length) return null;
  return (
    <section className="demo-chat-picker" aria-label="Demo company questions">
      <div className="demo-chat-picker-bar">
        <label htmlFor="demo-chat-company">
          <Globe size={15} />
          Demo company files
        </label>
        <select
          id="demo-chat-company"
          aria-label="Demo company files"
          value={selected?.id || ""}
          disabled={disabled}
          onChange={(event) => onSelect(event.target.value)}
        >
          <option value="">Your workspace files</option>
          {(["India", "Global"] as const).map((region) => (
            <optgroup
              label={
                region === "India" ? "Indian companies" : "Global companies"
              }
              key={region}
            >
              {companies
                .filter((company) => company.demo_region === region)
                .map((company) => (
                  <option key={company.id} value={company.id}>
                    {company.name}
                  </option>
                ))}
            </optgroup>
          ))}
        </select>
        {selected && (
          <button
            className="icon-button"
            aria-label={
              expanded ? "Hide company questions" : "Show company questions"
            }
            aria-expanded={expanded}
            onClick={() => setExpanded((value) => !value)}
          >
            <ChevronDown size={16} className={expanded ? "" : "closed"} />
          </button>
        )}
      </div>
      {selected && expanded && (
        <div className="demo-chat-question-panel">
          <div className="demo-chat-question-heading">
            <span>{selected.name} · 3 indexed files</span>
            <button
              disabled={disabled}
              onClick={() =>
                setQuestions(chooseQuestions(selected.demo_slug || ""))
              }
            >
              <RotateCcw size={12} />
              Refresh questions
            </button>
          </div>
          <div className="demo-chat-question-grid">
            {questions.map((question) => (
              <button
                className="demo-chat-question"
                key={question}
                disabled={disabled}
                title={question}
                onClick={() => onQuestion(question)}
              >
                <span>{question}</span>
                <ArrowUpRight size={13} />
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
