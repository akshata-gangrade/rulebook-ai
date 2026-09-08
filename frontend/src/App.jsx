import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { askQuestion } from "./services/api";
import "./index.css";

const SUGGESTIONS = [
  "What attendance percentage is required to sit an exam?",
  "What happens if I miss an exam for a family wedding?",
  "Can a committee waive the attendance requirement?",
];

const VERDICT_COPY = {
  ANSWERED: {
    word: "Answered",
    sub: "Backed by the evidence below",
    icon: "document",
  },
  CONFLICT: {
    word: "Conflicting",
    sub: "Two sections disagree — both are shown",
    icon: "conflict",
  },
};
const DEFAULT_VERDICT = {
  word: "Not covered",
  sub: "No clause in the rulebook applies",
  icon: "empty",
};

function statusKey(status) {
  return (status || "").toUpperCase();
}

function SearchIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <circle cx="9" cy="9" r="6.5" stroke="currentColor" strokeWidth="1.6" />
      <line x1="13.6" y1="13.6" x2="18" y2="18" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <line x1="3" y1="10" x2="16" y2="10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <polyline points="10.5,4 16.5,10 10.5,16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  );
}

function VerdictIcon({ type }) {
  if (type === "conflict") {
    return (
      <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path d="M10 3 L17.5 16.5 H2.5 Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
        <line x1="10" y1="8.2" x2="10" y2="12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        <circle cx="10" cy="14.4" r="0.9" fill="currentColor" />
      </svg>
    );
  }
  if (type === "empty") {
    return (
      <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <circle cx="10" cy="10" r="7.2" stroke="currentColor" strokeWidth="1.6" strokeDasharray="2.6 2.6" />
      </svg>
    );
  }
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M5.5 2.8h6.2L16 7.1v10.1a1 1 0 0 1-1 1h-9.5a1 1 0 0 1-1-1V3.8a1 1 0 0 1 1-1Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M11.7 2.8V7h4.3" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <line x1="6.8" y1="10.4" x2="13.2" y2="10.4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <line x1="6.8" y1="13.1" x2="13.2" y2="13.1" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

function App() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleAsk(overrideQuestion) {
    const source = overrideQuestion ?? question;
    const trimmedQuestion = source.trim();

    if (!trimmedQuestion) {
      setError("Please enter a question.");
      return;
    }

    if (overrideQuestion) {
      setQuestion(overrideQuestion);
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const data = await askQuestion(trimmedQuestion);
      setResult(data);
    } catch (err) {
      setError(
        err.message || "Something went wrong while asking the rulebook."
      );
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter") {
      event.preventDefault();
      handleAsk();
    }
  }

  const verdict = result
    ? VERDICT_COPY[statusKey(result.status)] || DEFAULT_VERDICT
    : null;
  const verdictClass = result
    ? statusKey(result.status).toLowerCase().replace(/_/g, "-")
    : "";
  const confidencePct = result ? Math.round(result.confidence * 100) : 0;

  return (
    <div className="app">
      <header className="masthead">
        <div className="wordmark-block">
          <div className="mark">§</div>
          <div>
            <p className="wordmark">Rulebook AI</p>
            <p className="tagline">
              Clear answers, grounded in the rules.
            </p>
          </div>
        </div>
        <div className="index-status">
          <span className="index-dot" />
          Index ready
        </div>
      </header>

      <div className="shell">
        <div className="searchbar">
          <span className="search-icon">
            <SearchIcon />
          </span>
          <input
            id="question-input"
            type="text"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about the university rulebook…"
            disabled={loading}
          />
          <button
            className="ask-button"
            onClick={() => handleAsk()}
            disabled={loading}
          >
            {loading ? "Searching…" : "Ask the rulebook"}
            {!loading && <ArrowIcon />}
          </button>
        </div>

        {error && <p className="error-note">{error}</p>}

        <div className="suggestions">
          <p className="suggestions-label">Try one of these</p>
          <div className="chip-row">
            {SUGGESTIONS.map((text) => (
              <button
                key={text}
                type="button"
                className="chip"
                onClick={() => handleAsk(text)}
                disabled={loading}
              >
                {text}
              </button>
            ))}
          </div>
        </div>

        <section className="results-panel" aria-live="polite">
          {!result && !loading && (
            <div className="empty-state">
              <p className="empty-state-lead">
                Ask a question above. The cited clauses will show up here,
                alongside which of three things happened.
              </p>
              <ul className="legend">
                <li>
                  <span className="legend-dot legend-dot--answered" />
                  <div>
                    <p className="legend-title">Answered</p>
                    <p className="legend-desc">
                      Backed by one or more cited clauses.
                    </p>
                  </div>
                </li>
                <li>
                  <span className="legend-dot legend-dot--conflict" />
                  <div>
                    <p className="legend-title">Conflicting</p>
                    <p className="legend-desc">
                      Two sections disagree, and both are shown.
                    </p>
                  </div>
                </li>
                <li>
                  <span className="legend-dot legend-dot--not-covered" />
                  <div>
                    <p className="legend-title">Not covered</p>
                    <p className="legend-desc">
                      The rulebook is silent — no clause applies.
                    </p>
                  </div>
                </li>
              </ul>
            </div>
          )}

          {loading && (
            <div className="loading-state" aria-busy="true">
              <div className="progress-line">
                <span />
              </div>
              <p>Reading the relevant clauses…</p>
            </div>
          )}

          {result && !loading && (
            <div className="result">
              <div className={`verdict-header verdict-${verdictClass}`}>
                <div className="verdict-top">
                  <span className={`verdict-icon verdict-icon--${verdictClass}`}>
                    <VerdictIcon type={verdict.icon} />
                  </span>
                  <div>
                    <p className="verdict-word">{verdict.word}</p>
                    <p className="verdict-sub">{verdict.sub}</p>
                  </div>
                </div>

                <div className="confidence-block">
                  <div
                    className="confidence-ring"
                    style={{ "--pct": confidencePct }}
                  >
                    <span className="confidence-value">{confidencePct}%</span>
                  </div>
                  <div className="confidence-copy">
                    <p className="confidence-title">Confidence</p>
                    <p className="confidence-caption">
                      Based on retrieved evidence
                    </p>
                  </div>
                </div>
              </div>

              {result.answer && (
                <div className="answer">
                  <ReactMarkdown>{result.answer}</ReactMarkdown>
                </div>
              )}

              {result.reason && (
                <p className="reason-note">
                  <span className="reason-label">Why: </span>
                  {result.reason}
                </p>
              )}

              {result.evidence?.length > 0 && (
                <div className="evidence">
                  <div className="evidence-heading">
                    <h2>Evidence</h2>
                    <span>
                      {result.evidence.length} source
                      {result.evidence.length !== 1 ? "s" : ""}
                    </span>
                  </div>

                  <ol className="citation-list">
                    {result.evidence.map((item, index) => (
                      <li className="citation" key={item.chunk_id}>
                        <span className="citation-number">§{index + 1}</span>
                        <div className="citation-body">
                          <p className="citation-section">
                            {item.section || "Rulebook"}
                          </p>
                          <p className="citation-text">
                            &ldquo;{item.text}&rdquo;
                          </p>
                          <p className="citation-source">
                            {item.source_file.split("\\").pop()}
                            {item.page ? `, page ${item.page}` : ""}
                          </p>
                        </div>
                        <div className="citation-score">
                          <span>{item.similarity.toFixed(2)} match</span>
                          <div className="score-meter">
                            <span
                              style={{
                                width: `${Math.min(
                                  100,
                                  Math.round(item.similarity * 100)
                                )}%`,
                              }}
                            />
                          </div>
                        </div>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default App;