const base = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

export function apiUrl(path) {
  return `${base}${path}`;
}

export async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(apiUrl(path), options);
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error(
      "Cannot reach CloudFlow. Check that the backend is running and try again.",
      { cause: error },
    );
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status}).`;
    try {
      const body = await response.json();
      detail =
        typeof body.detail === "string"
          ? body.detail
          : JSON.stringify(body.detail || detail);
    } catch {
      /* retain HTTP status */
    }
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

export function post(path, body) {
  return request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export const artifactUrl = (runId, path) =>
  apiUrl(
    `/runs/${runId}/artifacts/${path.split("/").map(encodeURIComponent).join("/")}`,
  );
export const artifactRequest = (runId, path, options) =>
  request(
    `/runs/${runId}/artifacts/${path.split("/").map(encodeURIComponent).join("/")}`,
    options,
  );
