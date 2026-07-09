/**
 * Fallback JSON-repair utilities. Groq's forced tool-calling makes these
 * rarely necessary (tool call arguments already arrive as a JSON string
 * matching our schema), but they exist as defense-in-depth for the case a
 * response is malformed - e.g. wrapped in prose or code fences.
 */

export function stripCodeFences(raw: string): string {
  return raw
    .trim()
    .replace(/^```(?:json)?\s*/i, "")
    .replace(/\s*```$/i, "")
    .trim();
}

export function extractFirstJsonObject(raw: string): string | null {
  const start = raw.indexOf("{");
  if (start === -1) return null;

  let depth = 0;
  for (let i = start; i < raw.length; i++) {
    if (raw[i] === "{") depth++;
    if (raw[i] === "}") {
      depth--;
      if (depth === 0) {
        return raw.slice(start, i + 1);
      }
    }
  }
  return null;
}

export function fixTrailingCommas(raw: string): string {
  return raw.replace(/,\s*([}\]])/g, "$1");
}

/**
 * Attempts to coerce a raw, possibly malformed string into a parsed JS
 * value. Returns null instead of throwing so callers can decide what to do
 * next (e.g. fall through to the retry path).
 */
export function repairAndParse(raw: string): unknown | null {
  const candidates = [raw, stripCodeFences(raw)];

  const extracted = extractFirstJsonObject(stripCodeFences(raw));
  if (extracted) {
    candidates.push(extracted, fixTrailingCommas(extracted));
  }

  for (const candidate of candidates) {
    try {
      return JSON.parse(fixTrailingCommas(candidate));
    } catch {
      // try the next candidate
    }
  }
  return null;
}
