import {
  apiPost,
  storeApiAccessToken,
} from "../../api/client";

import type {
  LoginRequest,
  LoginResponse,
} from "./types";


const AUTH_API_PREFIX = "/auth";


function normalizeEmail(
  value: string,
): string {
  const normalized = value.trim();

  if (!normalized) {
    throw new Error(
      "Email is required.",
    );
  }

  return normalized;
}


function validatePassword(
  value: string,
): string {
  if (!value) {
    throw new Error(
      "Password is required.",
    );
  }

  return value;
}


export async function loginTeacher(
  request: LoginRequest,
  signal?: AbortSignal,
): Promise<LoginResponse> {
  const payload: LoginRequest = {
    email: normalizeEmail(
      request.email,
    ),
    password: validatePassword(
      request.password,
    ),
  };

  const response = await apiPost<
    LoginResponse,
    LoginRequest
  >(
    `${AUTH_API_PREFIX}/login`,
    payload,
    {
      signal,
    },
  );

  if (
    !response.access_token ||
    !response.access_token.trim()
  ) {
    throw new Error(
      "Login succeeded, but the backend did not return an access token.",
    );
  }

  storeApiAccessToken(
    response.access_token,
  );

  return response;
}


export const authApi = {
  login: loginTeacher,
} as const;