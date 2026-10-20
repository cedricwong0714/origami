/**
 * Read a calculator response.
 *
 * The studio calls `/api/...`. When that route is missing, the host returns
 * an HTML page whose first word is "The". `response.json()` then throws
 * `Unexpected token 'T'`. Callers should use this helper so the screen
 * shows the connection failure instead of a JSON parse error.
 */

export async function readApiJson<T>(response: Response): Promise<T> {
  const text = await response.text();
  const trimmed = text.trim();
  const looksJson = trimmed.startsWith("{") || trimmed.startsWith("[");
  if (!looksJson) {
    throw new Error(
      "The calculator is not connected on this host. The request returned a web page instead of model data, so this field cannot run. Start the Python API (port 41287) and open the studio through that same server.",
    );
  }
  let body: T & { detail?: unknown };
  try {
    body = JSON.parse(trimmed) as T & { detail?: unknown };
  } catch {
    throw new Error("The calculator returned text that is not model data.");
  }
  if (!response.ok) {
    const detail =
      typeof body.detail === "string" && body.detail.length > 0
        ? body.detail
        : `The calculator returned status ${response.status}.`;
    throw new Error(detail);
  }
  return body;
}
