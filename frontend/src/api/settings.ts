const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export type LlmProviderId = "chatgpt" | "claude" | "gemini";

export interface SettingsAccount {
  id: number;
  username: string;
  isAuthenticated: boolean;
}

export interface SettingsLifeArea {
  id: number;
  name: string;
  description: string;
}

export interface SettingsSkill {
  id: number;
  name: string;
  lifeArea: {
    id: number;
    name: string;
  } | null;
}

export interface SettingsActivityReward {
  skill: {
    id: number;
    name: string;
  };
  xpPerMinute: number;
}

export interface SettingsActivityDefinition {
  id: number;
  name: string;
  description: string;
  lifeArea: {
    id: number;
    name: string;
  } | null;
  rewards: SettingsActivityReward[];
}

export interface LlmProviderConfig {
  provider: LlmProviderId;
  label: string;
  modelName: string;
  isEnabled: boolean;
  apiKeySet: boolean;
  apiKeyPreview: string;
}

export interface AppSettings {
  account: SettingsAccount;
  llmProviders: LlmProviderConfig[];
  skills: SettingsSkill[];
  lifeAreas: SettingsLifeArea[];
  activityDefinitions: SettingsActivityDefinition[];
}

export interface AccountSettingsPayload {
  username?: string;
  password?: string;
}

export interface LlmProviderPayload {
  provider: LlmProviderId;
  modelName?: string;
  apiKey?: string;
  isEnabled?: boolean;
}

export interface SkillPayload {
  name: string;
  lifeAreaId?: number | null;
}

export interface ActivityDefinitionPayload {
  name: string;
  description?: string;
  lifeAreaId?: number | null;
  rewards: Array<{
    skillId: number;
    xpPerMinute: number;
  }>;
}

type RawSettingsAccount = {
  id: number;
  username: string;
  is_authenticated: boolean;
};

type RawLifeArea = {
  id: number;
  name: string;
  description: string;
};

type RawSkill = {
  id: number;
  name: string;
  life_area: {
    id: number;
    name: string;
  } | null;
};

type RawActivityDefinition = {
  id: number;
  name: string;
  description: string;
  life_area: {
    id: number;
    name: string;
  } | null;
  rewards: Array<{
    skill: {
      id: number;
      name: string;
    };
    xp_per_minute: number;
  }>;
};

type RawLlmProviderConfig = {
  provider: LlmProviderId;
  label: string;
  model_name: string;
  is_enabled: boolean;
  api_key_set: boolean;
  api_key_preview: string;
};

type RawAppSettingsResponse = {
  account: RawSettingsAccount;
  llm_providers: RawLlmProviderConfig[];
  skills: RawSkill[];
  life_areas: RawLifeArea[];
  activity_definitions: RawActivityDefinition[];
};

type RawAccountSettingsResponse = {
  account: RawSettingsAccount;
};

type RawLlmSettingsResponse = {
  llm_providers: RawLlmProviderConfig[];
};

type RawSkillResponse = {
  skill: RawSkill;
};

type RawActivityDefinitionResponse = {
  activity_definition: RawActivityDefinition;
};

function getCookie(name: string): string {
  const cookie = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`));

  return cookie ? decodeURIComponent(cookie.split("=")[1] ?? "") : "";
}

async function requestJson<TResponse>(
  path: string,
  init: RequestInit = {}
): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers
    },
    ...init
  });

  if (!response.ok) {
    let message = `Request failed: ${response.status} ${response.statusText}`;
    try {
      const payload = (await response.json()) as { error?: { message?: string } };
      message = payload.error?.message ?? message;
    } catch {
      // Keep the generic response message when the body is not JSON.
    }
    throw new Error(message);
  }

  return response.json() as Promise<TResponse>;
}

function transformAccount(raw: RawSettingsAccount): SettingsAccount {
  return {
    id: raw.id,
    username: raw.username,
    isAuthenticated: raw.is_authenticated
  };
}

function transformSkill(raw: RawSkill): SettingsSkill {
  return {
    id: raw.id,
    name: raw.name,
    lifeArea: raw.life_area
  };
}

function transformActivityDefinition(
  raw: RawActivityDefinition
): SettingsActivityDefinition {
  return {
    id: raw.id,
    name: raw.name,
    description: raw.description,
    lifeArea: raw.life_area,
    rewards: raw.rewards.map((reward) => ({
      skill: reward.skill,
      xpPerMinute: reward.xp_per_minute
    }))
  };
}

function transformLlmProvider(raw: RawLlmProviderConfig): LlmProviderConfig {
  return {
    provider: raw.provider,
    label: raw.label,
    modelName: raw.model_name,
    isEnabled: raw.is_enabled,
    apiKeySet: raw.api_key_set,
    apiKeyPreview: raw.api_key_preview
  };
}

function transformAppSettings(raw: RawAppSettingsResponse): AppSettings {
  return {
    account: transformAccount(raw.account),
    llmProviders: raw.llm_providers.map(transformLlmProvider),
    skills: raw.skills.map(transformSkill),
    lifeAreas: raw.life_areas,
    activityDefinitions: raw.activity_definitions.map(transformActivityDefinition)
  };
}

export async function fetchAppSettings(): Promise<AppSettings> {
  const raw = await requestJson<RawAppSettingsResponse>("/api/app-settings/");
  return transformAppSettings(raw);
}

export async function saveAccountSettings(
  payload: AccountSettingsPayload
): Promise<SettingsAccount> {
  const raw = await requestJson<RawAccountSettingsResponse>("/api/app-settings/account/", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: JSON.stringify({
      username: payload.username,
      password: payload.password
    })
  });
  return transformAccount(raw.account);
}

export async function saveLlmSettings(
  providers: LlmProviderPayload[]
): Promise<LlmProviderConfig[]> {
  const raw = await requestJson<RawLlmSettingsResponse>("/api/app-settings/llm/", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: JSON.stringify({
      providers: providers.map((provider) => ({
        provider: provider.provider,
        model_name: provider.modelName,
        api_key: provider.apiKey,
        is_enabled: provider.isEnabled
      }))
    })
  });
  return raw.llm_providers.map(transformLlmProvider);
}

export async function createSkill(payload: SkillPayload): Promise<SettingsSkill> {
  const raw = await requestJson<RawSkillResponse>("/api/skills/", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: JSON.stringify({
      name: payload.name,
      life_area_id: payload.lifeAreaId
    })
  });
  return transformSkill(raw.skill);
}

export async function createActivityDefinition(
  payload: ActivityDefinitionPayload
): Promise<SettingsActivityDefinition> {
  const raw = await requestJson<RawActivityDefinitionResponse>(
    "/api/activity-definitions/",
    {
      method: "POST",
      headers: {
        "X-CSRFToken": getCookie("csrftoken")
      },
      body: JSON.stringify({
        name: payload.name,
        description: payload.description,
        life_area_id: payload.lifeAreaId,
        rewards: payload.rewards.map((reward) => ({
          skill_id: reward.skillId,
          xp_per_minute: reward.xpPerMinute
        }))
      })
    }
  );
  return transformActivityDefinition(raw.activity_definition);
}
