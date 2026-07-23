import type { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

const fieldClass =
  "w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-muted focus:outline-none focus:ring-1 focus:ring-brand focus:border-brand";

const labelTextClass = "mb-1.5 block text-sm text-ink-muted";

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  help?: string;
}

export function TextField({ label, help, className = "", ...props }: TextFieldProps) {
  const input = <input className={`${fieldClass} ${className}`} {...props} />;
  return (
    <div>
      {label ? (
        <label>
          <span className={labelTextClass}>{label}</span>
          {input}
        </label>
      ) : (
        input
      )}
      {help && <p className="mt-1 text-xs text-ink-muted">{help}</p>}
    </div>
  );
}

interface TextAreaFieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
}

export function TextAreaField({ label, className = "", ...props }: TextAreaFieldProps) {
  const textarea = <textarea className={`${fieldClass} resize-y ${className}`} {...props} />;
  return (
    <div>
      {label ? (
        <label>
          <span className={labelTextClass}>{label}</span>
          {textarea}
        </label>
      ) : (
        textarea
      )}
    </div>
  );
}

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
}

export function SelectField({ label, className = "", children, ...props }: SelectFieldProps) {
  const select = (
    <select className={`${fieldClass} ${className}`} {...props}>
      {children}
    </select>
  );
  return (
    <div>
      {label ? (
        <label>
          <span className={labelTextClass}>{label}</span>
          {select}
        </label>
      ) : (
        select
      )}
    </div>
  );
}
