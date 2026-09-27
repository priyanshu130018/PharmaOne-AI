import React from "react";

export function Field({
  label,
  htmlFor,
  error,
  help,
  children,
  required,
  badge,
  isHighlighted = false,
  className = "",
}) {
  return (
    <div
      data-testid={htmlFor ? `field-container-${htmlFor}` : undefined}
      data-field={htmlFor}
      className={`rounded-lg transition-all duration-200 ${
        isHighlighted
          ? "bg-emerald-50/90 border border-emerald-400 p-2.5 ring-1 ring-emerald-300 shadow-xs"
          : "border border-transparent p-0"
      } ${className}`}
    >
      {label && (
        <div className="mb-1 flex items-center justify-between gap-1">
          <label htmlFor={htmlFor} className="field-label mb-0">
            {label}
            {required && <span className="ml-1 text-red-500">*</span>}
          </label>
          <div className="flex items-center gap-1.5">
            {badge}
          </div>
        </div>
      )}
      {children}
      {error ? (
        <p className="mt-1 text-xs text-red-600">{error}</p>
      ) : help ? (
        <p className="field-help">{help}</p>
      ) : null}
    </div>
  );
}

export function TextInput({ id, name, value, onChange, ...rest }) {
  return (
    <input
      id={id}
      name={name}
      value={value ?? ""}
      onChange={onChange}
      className="field-input"
      {...rest}
    />
  );
}

export function TextArea({ id, name, value, onChange, rows = 3, ...rest }) {
  return (
    <textarea
      id={id}
      name={name}
      value={value ?? ""}
      onChange={onChange}
      rows={rows}
      className="field-input resize-y"
      {...rest}
    />
  );
}

export function Select({ id, name, value, onChange, options, placeholder, ...rest }) {
  return (
    <select
      id={id}
      name={name}
      value={value ?? ""}
      onChange={onChange}
      className="field-input"
      {...rest}
    >
      {placeholder !== undefined && <option value="">{placeholder}</option>}
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

export function Button({ variant = "primary", className = "", children, ...rest }) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50";
  const variants = {
    primary:
      "bg-brand-600 text-white hover:bg-brand-700 focus:ring-brand-300 shadow-sm",
    secondary:
      "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 focus:ring-slate-200",
    ghost: "text-brand-700 hover:bg-brand-50 focus:ring-brand-200",
  };
  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...rest}>
      {children}
    </button>
  );
}

export function Badge({ className = "", children }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${className}`}
    >
      {children}
    </span>
  );
}

export function SectionHeading({ children }) {
  return (
    <h3 className="section-title mt-1 border-b border-slate-100 pb-1">{children}</h3>
  );
}

export function AiFieldBadge({ isAi }) {
  if (isAi) {
    return (
      <span
        title="Automatically extracted by AI assistant"
        className="inline-flex items-center gap-1 rounded border border-brand-200/80 bg-brand-50 px-1.5 py-0.5 text-[10px] font-medium text-brand-700"
      >
        <svg className="h-2.5 w-2.5 text-brand-600" fill="currentColor" viewBox="0 0 20 20">
          <path d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" />
        </svg>
        AI extracted
      </span>
    );
  }
  return null;
}
