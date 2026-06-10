import {
  Bot,
  KeyRound,
  Languages,
  Palette,
  Plus,
  RotateCcw,
  ShieldCheck,
  UserRound
} from "lucide-react";
import type { FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";

import {
  createActivityDefinition,
  createSkill,
  fetchAppSettings,
  saveAccountSettings,
  saveLlmSettings
} from "../api/settings";
import type {
  AppSettings,
  LlmProviderConfig,
  LlmProviderId,
  SettingsSkill
} from "../api/settings";
import type { ThemeId } from "../theme";
import { languageOptions, useI18n } from "../i18n";
import { ThemeSwitcher } from "./ThemeSwitcher";

interface SettingsViewProps {
  apiStatus: string;
  isApiReady: boolean;
  theme: ThemeId;
  onThemeChange: (theme: ThemeId) => void;
  onCatalogChanged: () => Promise<void>;
}

interface LlmProviderFormRow extends LlmProviderConfig {
  apiKey: string;
}

interface ActivityRewardRow {
  skillId: string;
  xpPerMinute: number;
}

const defaultProviderLabels: Record<LlmProviderId, string> = {
  chatgpt: "ChatGPT",
  claude: "Claude",
  gemini: "Gemini"
};

const providerOrder: LlmProviderId[] = ["chatgpt", "claude", "gemini"];

function defaultLlmRows(): LlmProviderFormRow[] {
  return providerOrder.map((provider) => ({
    provider,
    label: defaultProviderLabels[provider],
    modelName: "",
    isEnabled: false,
    apiKeySet: false,
    apiKeyPreview: "",
    apiKey: ""
  }));
}

export function SettingsView({
  apiStatus,
  isApiReady,
  theme,
  onThemeChange,
  onCatalogChanged
}: SettingsViewProps) {
  const { language, setLanguage, t } = useI18n();
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSavingAccount, setIsSavingAccount] = useState(false);
  const [isSavingLlm, setIsSavingLlm] = useState(false);
  const [isSavingSkill, setIsSavingSkill] = useState(false);
  const [isSavingActivity, setIsSavingActivity] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [llmRows, setLlmRows] = useState<LlmProviderFormRow[]>(defaultLlmRows);
  const [skillName, setSkillName] = useState("");
  const [skillLifeAreaId, setSkillLifeAreaId] = useState("");
  const [activityName, setActivityName] = useState("");
  const [activityDescription, setActivityDescription] = useState("");
  const [activityLifeAreaId, setActivityLifeAreaId] = useState("");
  const [activityRewards, setActivityRewards] = useState<ActivityRewardRow[]>([
    { skillId: "", xpPerMinute: 1 }
  ]);

  async function refreshSettings() {
    if (!isApiReady) {
      return;
    }

    setIsLoading(true);
    try {
      const nextSettings = await fetchAppSettings();
      setSettings(nextSettings);
      setUsername(nextSettings.account.username);
      setLlmRows(
        nextSettings.llmProviders.map((provider) => ({
          ...provider,
          apiKey: ""
        }))
      );
      setActivityRewards((current) =>
        current.map((reward, index) => ({
          ...reward,
          skillId: reward.skillId || nextSettings.skills[index]?.id.toString() || ""
        }))
      );
      setStatus(null);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("settings.apiUnavailable"));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void refreshSettings();
  }, [isApiReady]);

  const firstSkillId = settings?.skills[0]?.id.toString() ?? "";
  const hasSkills = Boolean(settings?.skills.length);

  const activityRewardSkillIds = useMemo(
    () => new Set(activityRewards.map((reward) => reward.skillId).filter(Boolean)),
    [activityRewards]
  );

  async function handleAccountSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isApiReady) {
      setStatus(t("settings.accountApiRequired"));
      return;
    }

    setIsSavingAccount(true);
    try {
      const account = await saveAccountSettings({
        username: username.trim(),
        password: password.trim() || undefined
      });
      setUsername(account.username);
      setPassword("");
      setStatus(t("settings.accountSaved"));
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("settings.accountSaveFailed"));
    } finally {
      setIsSavingAccount(false);
    }
  }

  async function handleLlmSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isApiReady) {
      setStatus(t("settings.llmApiRequired"));
      return;
    }

    setIsSavingLlm(true);
    try {
      const savedProviders = await saveLlmSettings(
        llmRows.map((row) => ({
          provider: row.provider,
          modelName: row.modelName.trim(),
          isEnabled: row.isEnabled,
          ...(row.apiKey.trim() ? { apiKey: row.apiKey.trim() } : {})
        }))
      );
      setLlmRows(savedProviders.map((provider) => ({ ...provider, apiKey: "" })));
      setStatus(t("settings.llmSaved"));
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("settings.llmSaveFailed"));
    } finally {
      setIsSavingLlm(false);
    }
  }

  async function handleSkillSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isApiReady) {
      setStatus(t("settings.skillApiRequired"));
      return;
    }

    setIsSavingSkill(true);
    try {
      await createSkill({
        name: skillName.trim(),
        lifeAreaId: skillLifeAreaId ? Number(skillLifeAreaId) : null
      });
      setSkillName("");
      await refreshSettings();
      await onCatalogChanged();
      setStatus(t("settings.skillCreated"));
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("settings.skillSaveFailed"));
    } finally {
      setIsSavingSkill(false);
    }
  }

  async function handleActivitySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isApiReady) {
      setStatus(t("settings.activityApiRequired"));
      return;
    }

    const cleanRewards = activityRewards
      .filter((reward) => reward.skillId)
      .map((reward) => ({
        skillId: Number(reward.skillId),
        xpPerMinute: reward.xpPerMinute
      }));

    setIsSavingActivity(true);
    try {
      await createActivityDefinition({
        name: activityName.trim(),
        description: activityDescription.trim(),
        lifeAreaId: activityLifeAreaId ? Number(activityLifeAreaId) : null,
        rewards: cleanRewards
      });
      setActivityName("");
      setActivityDescription("");
      setActivityRewards([{ skillId: firstSkillId, xpPerMinute: 1 }]);
      await refreshSettings();
      await onCatalogChanged();
      setStatus(t("settings.activityTypeCreated"));
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("settings.activitySaveFailed"));
    } finally {
      setIsSavingActivity(false);
    }
  }

  function updateLlmRow(provider: LlmProviderId, changes: Partial<LlmProviderFormRow>) {
    setLlmRows((current) =>
      current.map((row) => (row.provider === provider ? { ...row, ...changes } : row))
    );
  }

  function updateActivityReward(index: number, changes: Partial<ActivityRewardRow>) {
    setActivityRewards((current) =>
      current.map((reward, rewardIndex) =>
        rewardIndex === index ? { ...reward, ...changes } : reward
      )
    );
  }

  function addActivityReward() {
    const nextSkill = settings?.skills.find(
      (skill) => !activityRewardSkillIds.has(skill.id.toString())
    );
    setActivityRewards((current) => [
      ...current,
      { skillId: nextSkill?.id.toString() ?? firstSkillId, xpPerMinute: 1 }
    ]);
  }

  function removeActivityReward(index: number) {
    setActivityRewards((current) =>
      current.length <= 1 ? current : current.filter((_, rewardIndex) => rewardIndex !== index)
    );
  }

  return (
    <section className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
      <div className="space-y-4">
        <article className="panel p-4">
          <div className="section-heading">
            <div>
              <p className="eyebrow">{t("settings.interface")}</p>
              <h2>{t("common.theme")}</h2>
            </div>
            <span>{theme}</span>
          </div>
          <div className="mt-4 flex items-start gap-3">
            <Palette className="mt-1 text-xp" size={18} />
            <div className="min-w-0 flex-1">
              <ThemeSwitcher value={theme} onChange={onThemeChange} />
            </div>
          </div>
        </article>

        <article className="panel p-4">
          <div className="section-heading">
            <div>
              <p className="eyebrow">i18n</p>
              <h2>{t("settings.language")}</h2>
            </div>
            <span>{language.toUpperCase()}</span>
          </div>
          <div className="mt-4 flex items-start gap-3">
            <Languages className="mt-1 text-xp" size={18} />
            <div className="min-w-0 flex-1">
              <div className="theme-switcher" aria-label={t("settings.language")}>
                {languageOptions.map((option) => (
                  <button
                    aria-pressed={language === option.id}
                    className={`theme-option ${language === option.id ? "theme-option-active" : ""}`}
                    key={option.id}
                    onClick={() => setLanguage(option.id)}
                    type="button"
                  >
                    <span>{option.shortLabel}</span>
                    <span>{option.label}</span>
                  </button>
                ))}
              </div>
              <p className="mt-3 text-sm leading-6 text-zinc-500">
                {t("settings.languageDescription")}
              </p>
            </div>
          </div>
        </article>

        <article className="panel p-4">
          <div className="section-heading">
            <div>
              <p className="eyebrow">{t("settings.account")}</p>
              <h2>{t("settings.profile")}</h2>
            </div>
            <span>{settings?.account.username ?? t("settings.local")}</span>
          </div>
          <form className="mt-4 space-y-4" onSubmit={handleAccountSubmit}>
            <label className="field-label">
              {t("settings.username")}
              <input
                className="field-control"
                disabled={!isApiReady || isSavingAccount}
                onChange={(event) => setUsername(event.target.value)}
                value={username}
              />
            </label>
            <label className="field-label">
              {t("settings.newPassword")}
              <input
                className="field-control"
                disabled={!isApiReady || isSavingAccount}
                minLength={8}
                onChange={(event) => setPassword(event.target.value)}
                placeholder={t("settings.passwordPlaceholder")}
                type="password"
                value={password}
              />
            </label>
            <button
              className="primary-button inline-flex items-center justify-center gap-2"
              disabled={!isApiReady || isSavingAccount || !username.trim()}
              type="submit"
            >
              <UserRound size={16} />
              {isSavingAccount ? t("common.saving") : t("settings.saveAccount")}
            </button>
          </form>
        </article>

        <article className="panel p-4">
          <div className="section-heading">
            <div>
              <p className="eyebrow">{t("settings.system")}</p>
              <h2>{t("settings.api")}</h2>
            </div>
            <span>{isApiReady ? t("common.live") : t("common.preview")}</span>
          </div>
          <p className="mt-4 text-sm leading-6 text-zinc-500">{apiStatus}</p>
          <button
            className="mt-4 inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm text-zinc-400 transition hover:border-xp/40 hover:text-xp"
            disabled={!isApiReady || isLoading}
            onClick={() => void refreshSettings()}
            type="button"
          >
            <RotateCcw size={15} />
            {t("common.refresh")}
          </button>
        </article>
      </div>

      <div className="space-y-4">
        <article className="panel p-4">
          <div className="section-heading">
            <div>
              <p className="eyebrow">{t("settings.llm")}</p>
              <h2>{t("settings.modelsAndKeys")}</h2>
            </div>
            <span>{llmRows.filter((row) => row.isEnabled).length} {t("common.enabledSuffix")}</span>
          </div>
          <form className="mt-4 space-y-3" onSubmit={handleLlmSubmit}>
            {llmRows.map((row) => (
              <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3" key={row.provider}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="inline-flex items-center gap-2">
                    <Bot className="text-xp" size={17} />
                    <div>
                      <p className="text-sm font-semibold text-zinc-100">{row.label}</p>
                      <p className="text-xs text-zinc-500">
                        {row.apiKeySet
                          ? `${t("settings.keySet")}: ${row.apiKeyPreview}`
                          : t("settings.noKeySaved")}
                      </p>
                    </div>
                  </div>
                  <label className="inline-flex items-center gap-2 text-sm text-zinc-400">
                    <input
                      checked={row.isEnabled}
                      disabled={!isApiReady || isSavingLlm}
                      onChange={(event) =>
                        updateLlmRow(row.provider, { isEnabled: event.target.checked })
                      }
                      type="checkbox"
                    />
                    {t("common.enabled")}
                  </label>
                </div>
                <div className="mt-3 grid gap-2 md:grid-cols-2">
                  <input
                    className="field-control mt-0"
                    disabled={!isApiReady || isSavingLlm}
                    onChange={(event) =>
                      updateLlmRow(row.provider, { modelName: event.target.value })
                    }
                    placeholder={t("settings.modelPlaceholder")}
                    value={row.modelName}
                  />
                  <div className="relative">
                    <KeyRound className="pointer-events-none absolute left-3 top-3 text-zinc-500" size={15} />
                    <input
                      className="field-control mt-0 pl-9"
                      disabled={!isApiReady || isSavingLlm}
                      onChange={(event) =>
                        updateLlmRow(row.provider, { apiKey: event.target.value })
                      }
                      placeholder={row.apiKeySet ? t("settings.replaceKey") : t("settings.apiKey")}
                      type="password"
                      value={row.apiKey}
                    />
                  </div>
                </div>
              </div>
            ))}
            <button
              className="primary-button inline-flex items-center justify-center gap-2"
              disabled={!isApiReady || isSavingLlm}
              type="submit"
            >
              <ShieldCheck size={16} />
              {isSavingLlm ? t("common.saving") : t("settings.saveLlm")}
            </button>
          </form>
        </article>

        <article className="panel p-4">
          <div className="section-heading">
            <div>
              <p className="eyebrow">{t("settings.catalog")}</p>
              <h2>{t("settings.skills")}</h2>
            </div>
            <span>{settings?.skills.length ?? 0}</span>
          </div>
          <form className="mt-4 grid gap-3 md:grid-cols-[1fr_0.8fr_auto]" onSubmit={handleSkillSubmit}>
            <input
              className="field-control mt-0"
              disabled={!isApiReady || isSavingSkill}
              onChange={(event) => setSkillName(event.target.value)}
              placeholder={t("settings.newSkill")}
              value={skillName}
            />
            <select
              className="field-control mt-0"
              disabled={!isApiReady || isSavingSkill}
              onChange={(event) => setSkillLifeAreaId(event.target.value)}
              value={skillLifeAreaId}
            >
              <option value="">{t("settings.noLifeArea")}</option>
              {settings?.lifeAreas.map((area) => (
                <option key={area.id} value={area.id}>
                  {area.name}
                </option>
              ))}
            </select>
            <button
              className="primary-button inline-flex items-center justify-center gap-2"
              disabled={!isApiReady || isSavingSkill || !skillName.trim()}
              type="submit"
            >
              <Plus size={16} />
              {t("common.add")}
            </button>
          </form>
          <div className="mt-4 flex flex-wrap gap-2">
            {settings?.skills.slice(0, 16).map((skill) => (
              <span
                className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-1.5 text-sm text-zinc-400"
                key={skill.id}
              >
                {skill.name}
              </span>
            ))}
          </div>
        </article>

        <article className="panel p-4">
          <div className="section-heading">
            <div>
              <p className="eyebrow">{t("settings.catalog")}</p>
              <h2>{t("settings.activityTypes")}</h2>
            </div>
            <span>{settings?.activityDefinitions.length ?? 0}</span>
          </div>
          <form className="mt-4 space-y-3" onSubmit={handleActivitySubmit}>
            <div className="grid gap-2 md:grid-cols-[1fr_0.8fr]">
              <input
                className="field-control mt-0"
                disabled={!isApiReady || isSavingActivity}
                onChange={(event) => setActivityName(event.target.value)}
                placeholder={t("settings.activityTypePlaceholder")}
                value={activityName}
              />
              <select
                className="field-control mt-0"
                disabled={!isApiReady || isSavingActivity}
                onChange={(event) => setActivityLifeAreaId(event.target.value)}
                value={activityLifeAreaId}
              >
                <option value="">{t("settings.noLifeArea")}</option>
                {settings?.lifeAreas.map((area) => (
                  <option key={area.id} value={area.id}>
                    {area.name}
                  </option>
                ))}
              </select>
            </div>
            <textarea
              className="field-control mt-0 min-h-20 resize-none"
              disabled={!isApiReady || isSavingActivity}
              onChange={(event) => setActivityDescription(event.target.value)}
              placeholder={t("settings.description")}
              value={activityDescription}
            />
            <div className="space-y-2">
              {activityRewards.map((reward, index) => (
                <div className="grid gap-2 md:grid-cols-[1fr_0.5fr_auto]" key={`${index}-${reward.skillId}`}>
                  <select
                    className="field-control mt-0"
                    disabled={!isApiReady || isSavingActivity || !hasSkills}
                    onChange={(event) =>
                      updateActivityReward(index, { skillId: event.target.value })
                    }
                    value={reward.skillId || firstSkillId}
                  >
                    {settings?.skills.map((skill: SettingsSkill) => (
                      <option key={skill.id} value={skill.id}>
                        {skill.name}
                      </option>
                    ))}
                  </select>
                  <input
                    className="field-control mt-0"
                    disabled={!isApiReady || isSavingActivity}
                    min={1}
                    onChange={(event) =>
                      updateActivityReward(index, {
                        xpPerMinute: Number(event.target.value)
                      })
                    }
                    type="number"
                    value={reward.xpPerMinute}
                  />
                  <button
                    className="rounded-lg border border-white/10 px-3 py-2 text-sm text-zinc-400 transition hover:border-epic/40 hover:text-epic"
                    disabled={!isApiReady || isSavingActivity || activityRewards.length <= 1}
                    onClick={() => removeActivityReward(index)}
                    type="button"
                  >
                    {t("settings.remove")}
                  </button>
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                className="rounded-lg border border-white/10 px-3 py-2 text-sm text-zinc-400 transition hover:border-xp/40 hover:text-xp"
                disabled={!isApiReady || isSavingActivity || !hasSkills}
                onClick={addActivityReward}
                type="button"
              >
                {t("settings.addSkillReward")}
              </button>
              <button
                className="primary-button inline-flex items-center justify-center gap-2"
                disabled={!isApiReady || isSavingActivity || !activityName.trim() || !hasSkills}
                type="submit"
              >
                <Plus size={16} />
                {isSavingActivity ? t("common.saving") : t("settings.createActivityType")}
              </button>
            </div>
          </form>
        </article>

        {status ? <p className="rounded-lg border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-zinc-400">{status}</p> : null}
      </div>
    </section>
  );
}
