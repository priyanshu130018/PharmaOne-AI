import React, { useRef, useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { updateMultipleFields } from "../features/deviations/deviationsSlice.js";
import { processDeviationInput } from "../features/assistant/assistantSlice.js";
import { api } from "../api/client.js";

export default function AiAssistantPanel() {
  const dispatch = useDispatch();
  const fileInputRef = useRef(null);
  const chatBottomRef = useRef(null);

  const [chatInput, setChatInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [isDragOver, setIsDragOver] = useState(false);

  const form = useSelector((s) => s.deviations?.form || {});
  const lastSaved = useSelector((s) => s.deviations?.lastSaved);
  const { extraction, assessment, meta, rawContent, extractedTextStatus } = useSelector(
    (s) => s.assistant || {}
  );

  const handleUploadFile = (file) => {
    if (!file) return;

    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const userMsg = {
      id: "u-" + Date.now(),
      sender: "user",
      text: `Uploaded ${file.name}`,
      timestamp: timeStr,
    };
    setChatMessages((prev) => [...prev, userMsg]);
    setIsUploading(true);

    dispatch(processDeviationInput({ file, mode: "upload" }))
      .unwrap()
      .then(() => {
        const botMsg = {
          id: "a-" + Date.now(),
          sender: "assistant",
          text: "I extracted the deviation details and populated the form. Please review the values on the left.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };
        setChatMessages((prev) => [...prev, botMsg]);
      })
      .catch((err) => {
        const errMsg = typeof err === "string" ? err : err?.message || "Could not process document.";
        const botMsg = {
          id: "a-" + Date.now(),
          sender: "assistant",
          text: `Processing error: ${errMsg}`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };
        setChatMessages((prev) => [...prev, botMsg]);
      })
      .finally(() => {
        setIsUploading(false);
        if (fileInputRef.current) fileInputRef.current.value = "";
      });
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) handleUploadFile(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleUploadFile(file);
  };

  const handleSendChat = async (e) => {
    e.preventDefault();
    const query = chatInput.trim();
    if (!query || isTyping || isUploading) return;

    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const userMsg = {
      id: "u-" + Date.now(),
      sender: "user",
      text: query,
      timestamp: timeStr,
    };

    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput("");
    setIsTyping(true);

    try {
      const savedAssessment =
        lastSaved?.ai_assessment ||
        (lastSaved?.ai_recommended_severity || lastSaved?.severity
          ? {
              recommended_severity: lastSaved.ai_recommended_severity || lastSaved.severity,
              severity: lastSaved.ai_recommended_severity || lastSaved.severity,
              recommended_impact: lastSaved.ai_recommended_impact || lastSaved.impact,
              impact: lastSaved.ai_recommended_impact || lastSaved.impact,
              reason: lastSaved.ai_reason,
              evidence: lastSaved.ai_evidence,
            }
          : null);

      const savedContext =
        lastSaved?.ai_extraction ||
        (lastSaved
          ? {
              site_plant: lastSaved.site_plant,
              title_short_description: lastSaved.title,
              detailed_description: lastSaved.description,
              deviation_type: lastSaved.deviation_type,
              batch_lot_number: lastSaved.batch_number,
              related_product_material: lastSaved.product_name,
            }
          : {});

      const res = await api.sendDeviationChat({
        message: query,
        context: extraction || meta?.deviation || savedContext,
        assessment: assessment || meta?.assessment || savedAssessment,
        currentForm: form || {},
        rawContent: rawContent || extractedTextStatus?.extractedText || "",
      });

      const rawChanges = res?.changes;
      let normalizedChanges = null;

      if (res?.intent === "update_form" && rawChanges) {
        if (Array.isArray(rawChanges) && rawChanges.length > 0) {
          normalizedChanges = rawChanges;
        } else if (typeof rawChanges === "object" && Object.keys(rawChanges).length > 0) {
          const fieldLabels = {
            site: "Site / Plant",
            site_plant: "Site / Plant",
            occurred_on: "Date of Occurrence",
            date_of_occurrence: "Date of Occurrence",
            detected_on: "Date Detected",
            title: "Title / Short Description",
            source: "Source Channel",
            product_name: "Related Product / Material",
            product: "Related Product / Material",
            product_code: "Product Code",
            batch_number: "Batch / Lot Number",
            description: "Detailed Description",
            deviation_type: "Deviation Type",
            impact: "Initial Impact",
            severity: "Initial Severity",
            parameter: "Parameter",
            expected_condition: "Approved Range",
            actual_condition: "Actual Value",
            duration: "Duration",
            manufacturing_stage: "Manufacturing Stage",
            equipment: "Equipment",
            department: "Department",
            responsible_team: "Responsible Team",
            immediate_action: "Immediate Action",
            qa_notified: "QA Notified",
            batch_status: "Batch Status",
          };
          normalizedChanges = Object.entries(rawChanges).map(([k, v]) => ({
            field: k,
            label: fieldLabels[k] || k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
            old_value: form[k] || "",
            new_value: v,
          }));
        }
      }

      // Live Form Update: If AI returned structured changes, update Redux immediately
      if (normalizedChanges && normalizedChanges.length > 0) {
        dispatch(updateMultipleFields({ changes: normalizedChanges }));
      }

      const botReply =
        res?.message ||
        res?.response ||
        "The provided deviation information does not contain enough information to answer that.";

      const botMsg = {
        id: "a-" + Date.now(),
        sender: "assistant",
        text: botReply,
        changes: normalizedChanges,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setChatMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      const botMsg = {
        id: "a-" + Date.now(),
        sender: "assistant",
        text:
          err?.message ||
          "The provided deviation information does not contain enough information to answer that.",
        changes: null,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setChatMessages((prev) => [...prev, botMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  useEffect(() => {
    if (chatBottomRef.current && typeof chatBottomRef.current.scrollIntoView === "function") {
      chatBottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [chatMessages, isTyping, isUploading]);

  return (
    <section
      aria-label="AI Deviation Assistant Panel"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`flex h-full flex-col rounded-xl border bg-white shadow-sm overflow-hidden transition ${
        isDragOver ? "border-blue-500 ring-2 ring-blue-100" : "border-slate-200"
      }`}
    >
      {/* Panel Header: Only AI Deviation Assistant */}
      <header className="shrink-0 flex items-center justify-between border-b border-slate-200 px-5 py-3.5 bg-white">
        <div className="flex items-center gap-2">
          <h2 className="text-base font-semibold text-slate-900">
            AI Deviation Assistant
          </h2>
          <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-bold text-blue-700 uppercase tracking-wider">
            BETA
          </span>
        </div>
        {(extraction || lastSaved) && (
          <span className="text-[10px] text-emerald-600 font-medium flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Deviation context active
          </span>
        )}
      </header>

      {/* Independently Scrollable Chat Conversation Area */}
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4 space-y-3">
        {chatMessages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center text-slate-400 p-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-50 text-blue-600 mb-3 shadow-xs">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="1.8"
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
            <p className="text-xs font-semibold text-slate-700 max-w-xs leading-relaxed">
              Describe your deviation or ask me to update any field in the form.
            </p>
            <p className="text-[11px] text-slate-400 mt-1 max-w-xs">
              Click 📎 to upload a deviation document or type an instruction below.
            </p>
          </div>
        ) : (
          chatMessages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-2.5 ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.sender === "assistant" && (
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white font-bold text-[10px] shadow-xs">
                  AI
                </div>
              )}
              <div
                className={`rounded-xl px-3.5 py-2.5 max-w-[85%] text-xs leading-relaxed shadow-xs ${
                  msg.sender === "user"
                    ? "bg-blue-600 text-white font-normal"
                    : "bg-white border border-slate-200 text-slate-800"
                }`}
              >
                {msg.sender === "assistant" && msg.changes && msg.changes.length > 0 ? (
                  <div className="space-y-2">
                    <div className="flex items-center gap-1.5 font-bold text-emerald-700 text-xs">
                      <span className="text-emerald-600 font-extrabold text-sm leading-none">✓</span>
                      <span>
                        {msg.changes.length === 1
                          ? "Change applied"
                          : `${msg.changes.length} changes applied`}
                      </span>
                    </div>
                    <div className="space-y-2.5 pl-1.5 border-l-2 border-emerald-500/30 ml-0.5">
                      {msg.changes.map((ch, idx) => (
                        <div key={idx} className="text-xs">
                          <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                            <span className="text-slate-400">•</span>
                            <span>{ch.label || ch.field}</span>
                          </div>
                          <div className="pl-3 mt-0.5 text-slate-700 font-medium text-[11px] break-words">
                            {ch.old_value &&
                            String(ch.old_value).trim() &&
                            String(ch.old_value).trim() !== String(ch.new_value).trim() ? (
                              <span>
                                <span className="text-slate-400 line-through mr-1.5">
                                  {String(ch.old_value)}
                                </span>
                                <span className="text-slate-400 mr-1.5">→</span>
                                <span className="font-semibold text-slate-900">
                                  {String(ch.new_value)}
                                </span>
                              </span>
                            ) : (
                              <span className="font-semibold text-slate-900">
                                {String(ch.new_value)}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                    {msg.text &&
                      !msg.text.match(/^\d+\s+changes?\s+applied\.?$/i) &&
                      !msg.text.match(/^change\s+applied\.?$/i) && (
                        <div className="text-slate-600 text-[11px] pt-1 border-t border-slate-100">
                          {msg.text}
                        </div>
                      )}
                  </div>
                ) : (
                  <div>{msg.text}</div>
                )}
              </div>
            </div>
          ))
        )}

        {/* Upload Processing Indicator */}
        {isUploading && (
          <div className="flex gap-2.5 justify-start">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white font-bold text-[10px]">
              AI
            </div>
            <div className="rounded-xl px-3.5 py-2 bg-blue-50 border border-blue-200 text-blue-800 text-xs flex items-center gap-2">
              <svg className="h-3.5 w-3.5 animate-spin text-blue-600 shrink-0" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <span>Extracting deviation details and populating form…</span>
            </div>
          </div>
        )}

        {/* Assistant Typing / Thinking Indicator */}
        {isTyping && (
          <div className="flex gap-2.5 justify-start">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white font-bold text-[10px]">
              AI
            </div>
            <div className="rounded-xl px-3.5 py-2 bg-white border border-slate-200 text-slate-500 text-xs flex items-center gap-1.5 shadow-2xs">
              <span className="h-1.5 w-1.5 rounded-full bg-blue-600 animate-bounce" />
              <span className="h-1.5 w-1.5 rounded-full bg-blue-600 animate-bounce [animation-delay:0.2s]" />
              <span className="h-1.5 w-1.5 rounded-full bg-blue-600 animate-bounce [animation-delay:0.4s]" />
              <span className="text-[11px] text-slate-400 ml-1">Thinking…</span>
            </div>
          </div>
        )}

        <div ref={chatBottomRef} />
      </div>

      {/* Fixed Bottom Chat Composer with integrated Attachment Icon */}
      <div className="shrink-0 border-t border-slate-200 px-4 py-3 bg-white rounded-b-xl">
        <form onSubmit={handleSendChat} className="flex items-center gap-2">
          {/* Hidden File Input for document upload */}
          <input
            ref={fileInputRef}
            id="pdf-upload-input"
            data-testid="document-upload-input"
            type="file"
            accept=".pdf,.txt,application/pdf,text/plain"
            onChange={handleFileChange}
            className="hidden"
          />

          {/* Attachment Icon Button */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading || isTyping}
            title="Attach deviation document (PDF, TXT)"
            aria-label="Attach document"
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 hover:text-blue-600 hover:bg-slate-100 transition disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
              />
            </svg>
          </button>

          {/* Chat Message Input */}
          <input
            type="text"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            disabled={isUploading || isTyping}
            placeholder="Ask me anything about this deviation..."
            className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-slate-50 disabled:text-slate-400"
          />

          {/* Send Message Button */}
          <button
            type="submit"
            disabled={!chatInput.trim() || isUploading || isTyping}
            aria-label="Send message"
            className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition shrink-0"
          >
            <svg
              className="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </form>
      </div>
    </section>
  );
}
