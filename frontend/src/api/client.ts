const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
)
  .trim()
  .replace(/\/+$/, "");

const DEFAULT_TIMEOUT_MS = 20_000;

type ApiRequestOptions = RequestInit & {
  timeoutMs?: number;
};

type ApiErrorBody = {
  detail?: unknown;
  message?: unknown;
  error?: unknown;
};

export class ApiError extends Error {
  readonly status: number;
  readonly url: string;
  readonly body: unknown;

  constructor({
    message,
    status,
    url,
    body,
  }: {
    message: string;
    status: number;
    url: string;
    body: unknown;
  }) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.url = url;
    this.body = body;
  }
}

function buildRequestUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

function extractErrorMessage(
  body: unknown,
  fallbackMessage: string
): string {
  if (typeof body === "string" && body.trim()) {
    return body.trim();
  }

  if (!body || typeof body !== "object") {
    return fallbackMessage;
  }

  const errorBody = body as ApiErrorBody;

  if (typeof errorBody.detail === "string" && errorBody.detail.trim()) {
    return errorBody.detail.trim();
  }

  if (Array.isArray(errorBody.detail)) {
    const validationMessages = errorBody.detail
      .map((item) => {
        if (!item || typeof item !== "object") {
          return null;
        }

        const record = item as Record<string, unknown>;
        const message =
          typeof record.msg === "string" ? record.msg : null;

        const location = Array.isArray(record.loc)
          ? record.loc.join(".")
          : null;

        if (message && location) {
          return `${location}: ${message}`;
        }

        return message;
      })
      .filter((item): item is string => Boolean(item));

    if (validationMessages.length > 0) {
      return validationMessages.join("; ");
    }
  }

  if (typeof errorBody.message === "string" && errorBody.message.trim()) {
    return errorBody.message.trim();
  }

  if (typeof errorBody.error === "string" && errorBody.error.trim()) {
    return errorBody.error.trim();
  }

  return fallbackMessage;
}

async function parseResponseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";

  if (response.status === 204) {
    return null;
  }

  const rawText = await response.text();

  if (!rawText.trim()) {
    return null;
  }

  if (contentType.includes("application/json")) {
    try {
      return JSON.parse(rawText);
    } catch {
      return rawText;
    }
  }

  return rawText;
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {}
): Promise<T> {
  const {
    timeoutMs = DEFAULT_TIMEOUT_MS,
    headers,
    signal: externalSignal,
    ...fetchOptions
  } = options;

  const requestUrl = buildRequestUrl(path);
  const controller = new AbortController();

  let externalAbortHandler: (() => void) | undefined;

  if (externalSignal) {
    externalAbortHandler = () => controller.abort();
    externalSignal.addEventListener("abort", externalAbortHandler, {
      once: true,
    });
  }

  const timeoutId = window.setTimeout(() => {
    controller.abort();
  }, timeoutMs);

  try {
    console.info("[API request]", {
      method: fetchOptions.method ?? "GET",
      url: requestUrl,
    });

    const response = await fetch(requestUrl, {
      ...fetchOptions,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...(headers ?? {}),
      },
    });

    const responseBody = await parseResponseBody(response);

    if (!response.ok) {
      const fallbackMessage =
        `Request failed with status ${response.status} ${response.statusText}`.trim();

      const message = extractErrorMessage(
        responseBody,
        fallbackMessage
      );

      console.error("[API error]", {
        method: fetchOptions.method ?? "GET",
        url: requestUrl,
        status: response.status,
        body: responseBody,
      });

      throw new ApiError({
        message,
        status: response.status,
        url: requestUrl,
        body: responseBody,
      });
    }

    console.info("[API response]", {
      method: fetchOptions.method ?? "GET",
      url: requestUrl,
      status: response.status,
    });

    return responseBody as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(
        `Request timed out after ${Math.round(timeoutMs / 1000)} seconds: ${requestUrl}`
      );
    }

    if (error instanceof TypeError) {
      throw new Error(
        `Unable to connect to the backend at ${requestUrl}. Check that the API is running on ${API_BASE_URL}.`
      );
    }

    throw error instanceof Error
      ? error
      : new Error("An unexpected API request error occurred.");
  } finally {
    window.clearTimeout(timeoutId);

    if (externalSignal && externalAbortHandler) {
      externalSignal.removeEventListener(
        "abort",
        externalAbortHandler
      );
    }
  }
}