/**
 * TaskForm — Create or edit a scraping task.
 *
 * Fields: name, url, extraction_type, selectors (dynamic list),
 * schedule (cron), policy_id dropdown.
 *
 * Uses useState-based form pattern (no external form library).
 */

import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { policies } from "../api/client";
import { useCreateTask, useUpdateTask } from "../hooks/useTasks";
import type { Task, ExtractionType, TaskCreate, TaskUpdate } from "../api/types";

interface TaskFormProps {
  /** Existing task to edit. If undefined, creates a new task. */
  task?: Task;
  /** Called after successful save or cancel. */
  onClose: () => void;
}

interface FormState {
  name: string;
  url: string;
  extraction_type: ExtractionType;
  selectors: string[];
  schedule: string;
  policy_id: string;
  priority: number;
}

function getInitialState(task?: Task): FormState {
  return {
    name: task?.name ?? "",
    url: task?.url ?? "",
    extraction_type: task?.extraction_type ?? "auto",
    selectors: task?.selectors?.length ? [...task.selectors] : [""],
    schedule: task?.schedule ?? "",
    policy_id: task?.policy_id ?? "",
    priority: task?.priority ?? 5,
  };
}

const EXTRACTION_TYPES: { value: ExtractionType; label: string }[] = [
  { value: "auto", label: "Auto-detect" },
  { value: "css", label: "CSS Selectors" },
  { value: "xpath", label: "XPath" },
  { value: "ai", label: "AI Extraction" },
];

export function TaskForm({ task, onClose }: TaskFormProps) {
  const [form, setForm] = useState<FormState>(() => getInitialState(task));
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({});

  const createMutation = useCreateTask();
  const updateMutation = useUpdateTask();
  const isEditing = !!task;
  const isPending = createMutation.isPending || updateMutation.isPending;
  const mutationError = createMutation.error || updateMutation.error;

  // Load policies for the dropdown
  const { data: policiesData } = useQuery({
    queryKey: ["policies", "form-dropdown"],
    queryFn: () => policies.list({ limit: 100 }),
  });

  const policyOptions = policiesData?.items ?? [];

  /* ── Field handlers ── */

  const setField = useCallback(
    <K extends keyof FormState>(key: K, value: FormState[K]) => {
      setForm((prev) => ({ ...prev, [key]: value }));
      setErrors((prev) => ({ ...prev, [key]: undefined }));
    },
    [],
  );

  const addSelector = useCallback(() => {
    setForm((prev) => ({ ...prev, selectors: [...prev.selectors, ""] }));
  }, []);

  const removeSelector = useCallback((index: number) => {
    setForm((prev) => ({
      ...prev,
      selectors: prev.selectors.filter((_, i) => i !== index),
    }));
  }, []);

  const updateSelector = useCallback((index: number, value: string) => {
    setForm((prev) => ({
      ...prev,
      selectors: prev.selectors.map((s, i) => (i === index ? value : s)),
    }));
  }, []);

  /* ── Validation ── */

  function validate(): boolean {
    const newErrors: Partial<Record<keyof FormState, string>> = {};

    if (!form.name.trim()) {
      newErrors.name = "Task name is required.";
    }

    if (!form.url.trim()) {
      newErrors.url = "URL is required.";
    } else {
      try {
        new URL(form.url);
      } catch {
        newErrors.url = "Must be a valid URL (e.g. https://example.com).";
      }
    }

    if (form.schedule.trim() && !/^[\d*,/\-\s]+$/.test(form.schedule.trim())) {
      newErrors.schedule = "Must be a valid cron expression.";
    }

    if (form.priority < 0 || form.priority > 10) {
      newErrors.priority = "Priority must be between 0 and 10.";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  /* ── Submit ── */

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    const cleanSelectors = form.selectors
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    if (isEditing) {
      const data: TaskUpdate = {
        name: form.name.trim(),
        url: form.url.trim(),
        extraction_type: form.extraction_type,
        selectors: cleanSelectors,
        schedule: form.schedule.trim() || null,
        policy_id: form.policy_id || null,
        priority: form.priority,
      };
      updateMutation.mutate(
        { taskId: task.id, data },
        { onSuccess: () => onClose() },
      );
    } else {
      const data: TaskCreate = {
        name: form.name.trim(),
        url: form.url.trim(),
        extraction_type: form.extraction_type,
        selectors: cleanSelectors,
        schedule: form.schedule.trim() || undefined,
        policy_id: form.policy_id || undefined,
        priority: form.priority,
      };
      createMutation.mutate(data, { onSuccess: () => onClose() });
    }
  }

  /* ── Render ── */

  return (
    <form onSubmit={handleSubmit} className="task-form">
      <div className="form-header">
        <h3>{isEditing ? "Edit Task" : "Create Task"}</h3>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={onClose}
          disabled={isPending}
        >
          Cancel
        </button>
      </div>

      {mutationError && (
        <div className="form-error-banner">
          {mutationError instanceof Error
            ? mutationError.message
            : "An error occurred."}
        </div>
      )}

      {/* Name */}
      <div className="form-group">
        <label htmlFor="task-name">Name</label>
        <input
          id="task-name"
          type="text"
          className={`form-input${errors.name ? " form-input--error" : ""}`}
          placeholder="My scraping task"
          value={form.name}
          onChange={(e) => setField("name", e.target.value)}
          disabled={isPending}
        />
        {errors.name && <span className="form-error">{errors.name}</span>}
      </div>

      {/* URL */}
      <div className="form-group">
        <label htmlFor="task-url">URL</label>
        <input
          id="task-url"
          type="text"
          className={`form-input${errors.url ? " form-input--error" : ""}`}
          placeholder="https://example.com/products"
          value={form.url}
          onChange={(e) => setField("url", e.target.value)}
          disabled={isPending}
        />
        {errors.url && <span className="form-error">{errors.url}</span>}
      </div>

      {/* Extraction Type */}
      <div className="form-group">
        <label htmlFor="task-extraction-type">Extraction Type</label>
        <select
          id="task-extraction-type"
          className="form-input"
          value={form.extraction_type}
          onChange={(e) =>
            setField("extraction_type", e.target.value as ExtractionType)
          }
          disabled={isPending}
        >
          {EXTRACTION_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      {/* Selectors (dynamic list) */}
      {(form.extraction_type === "css" || form.extraction_type === "xpath") && (
        <div className="form-group">
          <label>Selectors</label>
          <div className="selector-list">
            {form.selectors.map((selector, index) => (
              <div key={index} className="selector-row">
                <input
                  type="text"
                  className="form-input"
                  placeholder={
                    form.extraction_type === "css"
                      ? "div.product-card h2"
                      : "//div[@class='product']/h2"
                  }
                  value={selector}
                  onChange={(e) => updateSelector(index, e.target.value)}
                  disabled={isPending}
                />
                {form.selectors.length > 1 && (
                  <button
                    type="button"
                    className="btn btn-danger btn-sm"
                    onClick={() => removeSelector(index)}
                    disabled={isPending}
                    title="Remove selector"
                  >
                    X
                  </button>
                )}
              </div>
            ))}
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={addSelector}
              disabled={isPending}
            >
              + Add Selector
            </button>
          </div>
        </div>
      )}

      {/* Schedule */}
      <div className="form-group">
        <label htmlFor="task-schedule">Schedule (cron)</label>
        <input
          id="task-schedule"
          type="text"
          className={`form-input${errors.schedule ? " form-input--error" : ""}`}
          placeholder="*/30 * * * * (every 30 min) or leave empty for one-time"
          value={form.schedule}
          onChange={(e) => setField("schedule", e.target.value)}
          disabled={isPending}
        />
        {errors.schedule && (
          <span className="form-error">{errors.schedule}</span>
        )}
        <span className="form-hint">
          Leave empty for a one-time task. Use cron syntax for recurring.
        </span>
      </div>

      {/* Policy dropdown */}
      <div className="form-group">
        <label htmlFor="task-policy">Policy</label>
        <select
          id="task-policy"
          className="form-input"
          value={form.policy_id}
          onChange={(e) => setField("policy_id", e.target.value)}
          disabled={isPending}
        >
          <option value="">No policy (use defaults)</option>
          {policyOptions.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} ({p.preferred_lane})
            </option>
          ))}
        </select>
      </div>

      {/* Priority */}
      <div className="form-group">
        <label htmlFor="task-priority">
          Priority ({form.priority})
        </label>
        <input
          id="task-priority"
          type="range"
          min={0}
          max={10}
          step={1}
          className="form-range"
          value={form.priority}
          onChange={(e) => setField("priority", Number(e.target.value))}
          disabled={isPending}
        />
        <div className="form-range-labels">
          <span>0 (low)</span>
          <span>10 (high)</span>
        </div>
      </div>

      {/* Submit */}
      <div className="form-actions">
        <button
          type="button"
          className="btn btn-secondary"
          onClick={onClose}
          disabled={isPending}
        >
          Cancel
        </button>
        <button type="submit" className="btn btn-primary" disabled={isPending}>
          {isPending
            ? "Saving..."
            : isEditing
              ? "Update Task"
              : "Create Task"}
        </button>
      </div>
    </form>
  );
}
