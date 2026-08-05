const DEFAULT_API_BASE_URL =
  "http://127.0.0.1:8000/api";

const DEFAULT_TIMEOUT_MS = 20_000;

/**
 * The application has used more than one token key during development.
 * The API client checks these keys in order so all protected endpoints
 * use the same Bearer-token handling.
 */
const ACCESS_TOKEN_STORAGE_KEYS = [
  "misconceptionos_access_token",
  "access_token",
  "teacher_access_token",
] as const;

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  DEFAULT_API_BASE_URL
)
  .trim()
  .replace(/\/+$/, "");

export type QueryParameter =
  | string
  | number
  | boolean
  | null
  | undefined;

export type QueryParameters = Record<
  string,
  QueryParameter | QueryParameter[]
>;

export type ApiRequestOptions = Omit<
  RequestInit,
  "body"
> & {
  body?: BodyInit | object | null;
  timeoutMs?: number;
  query?: QueryParameters;
};

type ApiErrorBody = {
  detail?: unknown;
  message?: unknown;
  error?: unknown;
};

type TokenContainer = {
  access_token?: unknown;
  accessToken?: unknown;
  token?: unknown;
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

    Object.setPrototypeOf(
      this,
      ApiError.prototype
    );
  }
}

export class ApiTimeoutError extends Error {
  readonly timeoutMs: number;
  readonly url: string;

  constructor({
    timeoutMs,
    url,
  }: {
    timeoutMs: number;
    url: string;
  }) {
    super(
      `Request timed out after ${Math.round(
        timeoutMs / 1000
      )} seconds: ${url}`
    );

    this.name = "ApiTimeoutError";
    this.timeoutMs = timeoutMs;
    this.url = url;

    Object.setPrototypeOf(
      this,
      ApiTimeoutError.prototype
    );
  }
}

function normalizeAccessToken(
  value: unknown
): string | null {
  if (
    typeof value !== "string" ||
    !value.trim()
  ) {
    return null;
  }

  const normalized = value.trim();

  if (
    normalized.toLowerCase().startsWith(
      "bearer "
    )
  ) {
    const token = normalized
      .slice("bearer ".length)
      .trim();

    return token || null;
  }

  return normalized;
}

function extractTokenFromStoredValue(
  storedValue: string | null
): string | null {
  if (!storedValue) {
    return null;
  }

  const directToken =
    normalizeAccessToken(storedValue);

  /**
   * JWT access tokens normally begin with "eyJ".
   * Return direct string values immediately when they look like JWTs.
   */
  if (directToken?.startsWith("eyJ")) {
    return directToken;
  }

  try {
    const parsed =
      JSON.parse(storedValue) as unknown;

    if (
      parsed &&
      typeof parsed === "object"
    ) {
      const container =
        parsed as TokenContainer;

      return (
        normalizeAccessToken(
          container.access_token
        ) ??
        normalizeAccessToken(
          container.accessToken
        ) ??
        normalizeAccessToken(
          container.token
        )
      );
    }
  } catch {
    // The stored value is not JSON.
  }

  return directToken;
}

function getTokenFromStorage(
  storage: Storage
): string | null {
  for (
    const key of ACCESS_TOKEN_STORAGE_KEYS
  ) {
    const token =
      extractTokenFromStoredValue(
        storage.getItem(key)
      );

    if (token) {
      return token;
    }
  }

  return null;
}

export function getApiAccessToken():
  | string
  | null {
  if (typeof window === "undefined") {
    return null;
  }

  return (
    getTokenFromStorage(
      window.localStorage
    ) ??
    getTokenFromStorage(
      window.sessionStorage
    )
  );
}

export function storeApiAccessToken(
  accessToken: string
): void {
  if (typeof window === "undefined") {
    return;
  }

  const normalizedToken =
    normalizeAccessToken(accessToken);

  if (!normalizedToken) {
    throw new Error(
      "Cannot store an empty access token."
    );
  }

  window.localStorage.setItem(
    ACCESS_TOKEN_STORAGE_KEYS[0],
    normalizedToken
  );
}

export function clearApiAccessToken():
  void {
  if (typeof window === "undefined") {
    return;
  }

  for (
    const key of ACCESS_TOKEN_STORAGE_KEYS
  ) {
    window.localStorage.removeItem(key);
    window.sessionStorage.removeItem(key);
  }
}

export function hasApiAccessToken():
  boolean {
  return getApiAccessToken() !== null;
}

function appendQueryParameters(
  url: URL,
  query?: QueryParameters
): void {
  if (!query) {
    return;
  }

  Object.entries(query).forEach(
    ([key, rawValue]) => {
      const values = Array.isArray(
        rawValue
      )
        ? rawValue
        : [rawValue];

      values.forEach((value) => {
        if (
          value === undefined ||
          value === null ||
          value === ""
        ) {
          return;
        }

        url.searchParams.append(
          key,
          String(value)
        );
      });
    }
  );
}

function buildRequestUrl(
  path: string,
  query?: QueryParameters
): string {
  const normalizedPath =
    path.startsWith("/")
      ? path
      : `/${path}`;

  const url = new URL(
    `${API_BASE_URL}${normalizedPath}`
  );

  appendQueryParameters(
    url,
    query
  );

  return url.toString();
}

function extractErrorMessage(
  body: unknown,
  fallbackMessage: string
): string {
  if (
    typeof body === "string" &&
    body.trim()
  ) {
    return body.trim();
  }

  if (
    !body ||
    typeof body !== "object"
  ) {
    return fallbackMessage;
  }

  const errorBody =
    body as ApiErrorBody;

  if (
    typeof errorBody.detail ===
      "string" &&
    errorBody.detail.trim()
  ) {
    return errorBody.detail.trim();
  }

  if (
    Array.isArray(errorBody.detail)
  ) {
    const validationMessages =
      errorBody.detail
        .map((item) => {
          if (
            !item ||
            typeof item !== "object"
          ) {
            return null;
          }

          const record =
            item as Record<
              string,
              unknown
            >;

          const message =
            typeof record.msg ===
            "string"
              ? record.msg
              : null;

          const location =
            Array.isArray(record.loc)
              ? record.loc.join(".")
              : null;

          if (
            message &&
            location
          ) {
            return `${location}: ${message}`;
          }

          return message;
        })
        .filter(
          (
            item
          ): item is string =>
            Boolean(item)
        );

    if (
      validationMessages.length > 0
    ) {
      return validationMessages.join(
        "; "
      );
    }
  }

  if (
    typeof errorBody.message ===
      "string" &&
    errorBody.message.trim()
  ) {
    return errorBody.message.trim();
  }

  if (
    typeof errorBody.error ===
      "string" &&
    errorBody.error.trim()
  ) {
    return errorBody.error.trim();
  }

  return fallbackMessage;
}

async function parseResponseBody(
  response: Response
): Promise<unknown> {
  if (
    response.status === 204 ||
    response.status === 205
  ) {
    return null;
  }

  const rawText =
    await response.text();

  if (!rawText.trim()) {
    return null;
  }

  const contentType =
    response.headers.get(
      "content-type"
    ) ?? "";

  if (
    contentType.includes(
      "application/json"
    )
  ) {
    try {
      return JSON.parse(rawText);
    } catch {
      return rawText;
    }
  }

  return rawText;
}

function isJsonSerializableBody(
  body: ApiRequestOptions["body"]
): body is object {
  if (
    body === null ||
    body === undefined
  ) {
    return false;
  }

  if (
    typeof body !== "object" ||
    body instanceof FormData ||
    body instanceof Blob ||
    body instanceof URLSearchParams ||
    body instanceof ArrayBuffer
  ) {
    return false;
  }

  return true;
}

function prepareRequestBody(
  body: ApiRequestOptions["body"]
): BodyInit | null | undefined {
  if (
    isJsonSerializableBody(body)
  ) {
    return JSON.stringify(body);
  }

  return body as
    | BodyInit
    | null
    | undefined;
}

function prepareHeaders({
  headers,
  body,
}: {
  headers?: HeadersInit;
  body: ApiRequestOptions["body"];
}): Headers {
  const preparedHeaders =
    new Headers(headers);

  if (
    !preparedHeaders.has("Accept")
  ) {
    preparedHeaders.set(
      "Accept",
      "application/json"
    );
  }

  if (
    isJsonSerializableBody(body) &&
    !preparedHeaders.has(
      "Content-Type"
    )
  ) {
    preparedHeaders.set(
      "Content-Type",
      "application/json"
    );
  }

  /**
   * Respect an explicitly supplied Authorization header.
   * Otherwise inject the currently stored teacher access token.
   */
  if (
    !preparedHeaders.has(
      "Authorization"
    )
  ) {
    const accessToken =
      getApiAccessToken();

    if (accessToken) {
      preparedHeaders.set(
        "Authorization",
        `Bearer ${accessToken}`
      );
    }
  }

  return preparedHeaders;
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {}
): Promise<T> {
  const {
    timeoutMs = DEFAULT_TIMEOUT_MS,
    query,
    headers,
    body,
    signal: externalSignal,
    ...fetchOptions
  } = options;

  const requestUrl =
    buildRequestUrl(
      path,
      query
    );

  const controller =
    new AbortController();

  let didTimeout = false;

  let externalAbortHandler:
    | (() => void)
    | undefined;

  if (externalSignal) {
    externalAbortHandler = () => {
      controller.abort(
        externalSignal.reason
      );
    };

    if (
      externalSignal.aborted
    ) {
      externalAbortHandler();
    } else {
      externalSignal.addEventListener(
        "abort",
        externalAbortHandler,
        {
          once: true,
        }
      );
    }
  }

  const timeoutId =
    window.setTimeout(
      () => {
        didTimeout = true;
        controller.abort();
      },
      timeoutMs
    );

  const method =
    fetchOptions.method
      ?.toUpperCase() ??
    "GET";

  try {
    const response =
      await fetch(
        requestUrl,
        {
          ...fetchOptions,
          method,
          body:
            prepareRequestBody(
              body
            ),
          signal:
            controller.signal,
          headers:
            prepareHeaders({
              headers,
              body,
            }),
        }
      );

    const responseBody =
      await parseResponseBody(
        response
      );

    if (!response.ok) {
      const fallbackMessage =
        `Request failed with status ` +
        `${response.status} ` +
        `${response.statusText}`.trim();

      throw new ApiError({
        message:
          extractErrorMessage(
            responseBody,
            fallbackMessage
          ),
        status:
          response.status,
        url:
          requestUrl,
        body:
          responseBody,
      });
    }

    return responseBody as T;
  } catch (error) {
    if (
      error instanceof ApiError
    ) {
      throw error;
    }

    if (didTimeout) {
      throw new ApiTimeoutError({
        timeoutMs,
        url: requestUrl,
      });
    }

    if (
      externalSignal?.aborted ||
      (
        error instanceof DOMException &&
        error.name ===
          "AbortError"
      )
    ) {
      throw error;
    }

    if (
      error instanceof TypeError
    ) {
      throw new Error(
        `Unable to connect to the backend at ` +
        `${requestUrl}. Confirm that the API is ` +
        `running at ${API_BASE_URL}.`
      );
    }

    throw error instanceof Error
      ? error
      : new Error(
          "An unexpected API request error occurred."
        );
  } finally {
    window.clearTimeout(timeoutId);

    if (
      externalSignal &&
      externalAbortHandler
    ) {
      externalSignal.removeEventListener(
        "abort",
        externalAbortHandler
      );
    }
  }
}

export function apiGet<T>(
  path: string,
  options: Omit<
    ApiRequestOptions,
    "method" | "body"
  > = {}
): Promise<T> {
  return apiRequest<T>(
    path,
    {
      ...options,
      method: "GET",
    }
  );
}

export function apiPost<
  TResponse,
  TPayload extends object
>(
  path: string,
  payload: TPayload,
  options: Omit<
    ApiRequestOptions,
    "method" | "body"
  > = {}
): Promise<TResponse> {
  return apiRequest<TResponse>(
    path,
    {
      ...options,
      method: "POST",
      body: payload,
    }
  );
}

export function apiPut<
  TResponse,
  TPayload extends object
>(
  path: string,
  payload: TPayload,
  options: Omit<
    ApiRequestOptions,
    "method" | "body"
  > = {}
): Promise<TResponse> {
  return apiRequest<TResponse>(
    path,
    {
      ...options,
      method: "PUT",
      body: payload,
    }
  );
}

export function apiPatch<
  TResponse,
  TPayload extends object
>(
  path: string,
  payload: TPayload,
  options: Omit<
    ApiRequestOptions,
    "method" | "body"
  > = {}
): Promise<TResponse> {
  return apiRequest<TResponse>(
    path,
    {
      ...options,
      method: "PATCH",
      body: payload,
    }
  );
}

export function apiDelete<T>(
  path: string,
  options: Omit<
    ApiRequestOptions,
    "method" | "body"
  > = {}
): Promise<T> {
  return apiRequest<T>(
    path,
    {
      ...options,
      method: "DELETE",
    }
  );
}