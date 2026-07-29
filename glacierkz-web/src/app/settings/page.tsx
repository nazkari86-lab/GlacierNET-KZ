// GlacierNET-KZ Settings Page
"use client";

import { useEffect, useState } from "react";
import { useI18n } from "@/lib/I18nProvider";
import { type Locale } from "@/lib/i18n";
import { toast } from "@/components/Toast";
import { Tabs, TabPanel } from "@/components/TabsAccordion";
import {
  Settings,
  Globe,
  Bell,
  Shield,
  Database,
  Save,
  RotateCcw,
} from "lucide-react";

const TABS = [
  { key: "general", label: "General", icon: <Settings className="w-4 h-4" /> },
  { key: "language", label: "Language", icon: <Globe className="w-4 h-4" /> },
  { key: "notifications", label: "Notifications", icon: <Bell className="w-4 h-4" /> },
  { key: "security", label: "Security", icon: <Shield className="w-4 h-4" /> },
  { key: "data", label: "Data Management", icon: <Database className="w-4 h-4" /> },
];

const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "ru", label: "Русский" },
  { value: "kk", label: "Қазақша" },
] as const;

export default function SettingsPage() {
  const { t, locale, setLocale } = useI18n();
  const [activeTab, setActiveTab] = useState("general");

  // General
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
  const [workspaceName, setWorkspaceName] = useState("GlacierNET-KZ");
  const [darkMode, setDarkMode] = useState(false);
  const [autoSave, setAutoSave] = useState(true);

  // Language
  const [selectedLang, setSelectedLang] = useState<Locale>(locale);
  const [timezone, setTimezone] = useState("Asia/Almaty");

  // Notifications
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [slackNotifs, setSlackNotifs] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState("");

  // Security
  const [sessionTimeout, setSessionTimeout] = useState("60");
  const [mfaEnabled, setMfaEnabled] = useState(false);

  // Data Management
  const [cacheSize, setCacheSize] = useState<number | null>(null);
  const [storageUsed, setStorageUsed] = useState<number | null>(null);

  useEffect(() => {
    const stored = window.localStorage.getItem("glaciernet-kz.preferences");
    if (stored) {
      try {
        const value = JSON.parse(stored) as Record<string, unknown>;
        if (typeof value.workspaceName === "string") setWorkspaceName(value.workspaceName);
        if (typeof value.darkMode === "boolean") setDarkMode(value.darkMode);
        if (typeof value.autoSave === "boolean") setAutoSave(value.autoSave);
        if (typeof value.timezone === "string") setTimezone(value.timezone);
        if (typeof value.emailAlerts === "boolean") setEmailAlerts(value.emailAlerts);
        if (typeof value.slackNotifs === "boolean") setSlackNotifs(value.slackNotifs);
        if (typeof value.webhookUrl === "string") setWebhookUrl(value.webhookUrl);
        if (typeof value.sessionTimeout === "string") setSessionTimeout(value.sessionTimeout);
        if (typeof value.mfaEnabled === "boolean") setMfaEnabled(value.mfaEnabled);
      } catch { /* Ignore malformed local preference data. */ }
    }
    void navigator.storage?.estimate?.().then((estimate) => {
      setCacheSize(Math.round((estimate.usage || 0) / 1024 / 1024));
      setStorageUsed(estimate.quota ? Math.round(((estimate.usage || 0) / estimate.quota) * 100) : null);
    });
  }, []);

  const handleSave = () => {
    setLocale(selectedLang);
    document.documentElement.classList.toggle("dark", darkMode);
    window.localStorage.setItem("glaciernet-kz.preferences", JSON.stringify({ workspaceName, darkMode, autoSave, timezone, emailAlerts, slackNotifs, webhookUrl, sessionTimeout, mfaEnabled }));
    toast.success("Browser workspace preferences saved. API URL and credentials are deployment settings, not stored here.");
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-6 py-6">
          <div className="flex items-center gap-3">
            <Settings className="w-7 h-7 text-blue-600" />
            <h1 className="text-2xl font-bold text-gray-900">{t("settings.title")}</h1>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-6">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
          <Tabs tabs={TABS} active={activeTab} onChange={setActiveTab} />

          <div className="p-6">
            {/* General Tab */}
            <TabPanel active={activeTab} tab="general">
              <div className="space-y-6 max-w-2xl">
                <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 text-sm text-blue-900"><strong>API endpoint:</strong> {apiUrl || "same-origin / NEXT_PUBLIC_API_URL"}<p className="mt-1 text-xs">Set this when building or deploying the web app. It is intentionally not changeable from the browser.</p></div>

                <FieldGroup label="Workspace Name" htmlFor="workspace-name">
                  <input
                    id="workspace-name"
                    type="text"
                    value={workspaceName}
                    onChange={(e) => setWorkspaceName(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </FieldGroup>

                <ToggleRow label={t("settings.theme")} checked={darkMode} onChange={setDarkMode} description={t("settings.theme.dark")} />

                <ToggleRow label={t("settings.auto_save")} checked={autoSave} onChange={setAutoSave} description={t("common.enabled")} />
              </div>
            </TabPanel>

            {/* Language Tab */}
            <TabPanel active={activeTab} tab="language">
              <div className="space-y-6 max-w-2xl">
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-3">{t("settings.language")}</p>
                  <div className="space-y-2">
                    {LANGUAGES.map((lang) => (
                      <label
                        key={lang.value}
                        className="flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors hover:bg-gray-50"
                      >
                        <input
                          type="radio"
                          name="language"
                          value={lang.value}
                          checked={selectedLang === lang.value}
                          onChange={() => setSelectedLang(lang.value)}
                          className="w-4 h-4 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="text-sm text-gray-900">{lang.label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <FieldGroup label="Timezone" htmlFor="timezone">
                  <select
                    id="timezone"
                    value={timezone}
                    onChange={(e) => setTimezone(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white"
                  >
                    <option value="Asia/Almaty">Asia/Almaty (UTC+6)</option>
                    <option value="Asia/Astana">Asia/Astana (UTC+6)</option>
                    <option value="Asia/Oral">Asia/Oral (UTC+5)</option>
                    <option value="UTC">UTC</option>
                    <option value="Europe/Berlin">Europe/Berlin (UTC+1)</option>
                    <option value="America/New_York">America/New York (UTC-5)</option>
                  </select>
                </FieldGroup>
              </div>
            </TabPanel>

            {/* Notifications Tab */}
            <TabPanel active={activeTab} tab="notifications">
              <div className="space-y-6 max-w-2xl">
                <ToggleRow label={t("settings.email_notifications")} checked={emailAlerts} onChange={setEmailAlerts} />

                <ToggleRow label="Slack Notifications" checked={slackNotifs} onChange={setSlackNotifs} />

                <FieldGroup label="Webhook URL" htmlFor="webhook-url">
                  <input
                    id="webhook-url"
                    type="url"
                    value={webhookUrl}
                    onChange={(e) => setWebhookUrl(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    placeholder="https://hooks.slack.com/services/..."
                  />
                </FieldGroup>
              </div>
            </TabPanel>

            {/* Security Tab */}
            <TabPanel active={activeTab} tab="security">
              <div className="space-y-6 max-w-2xl">
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><strong>{t("settings.api_key")}:</strong> credentials are not stored or displayed in this browser. Configure API keys through the server environment or authenticated secret management.</div>

                <FieldGroup label={t("settings.timeout")} htmlFor="session-timeout">
                  <input
                    id="session-timeout"
                    type="number"
                    value={sessionTimeout}
                    onChange={(e) => setSessionTimeout(e.target.value)}
                    min={5}
                    max={480}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </FieldGroup>

                <ToggleRow
                  label="Multi-Factor Authentication"
                  checked={mfaEnabled}
                  onChange={setMfaEnabled}
                />
              </div>
            </TabPanel>

            {/* Data Management Tab */}
            <TabPanel active={activeTab} tab="data">
              <div className="space-y-6 max-w-2xl">
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                  <div>
                    <p className="text-sm font-medium text-gray-700">{t("settings.cache_size")}</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">{cacheSize === null ? "—" : `${cacheSize} MB`}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => { window.localStorage.removeItem("glaciernet-kz.preferences"); toast.info("Saved browser preferences cleared. Browser HTTP cache is controlled by your browser."); }}
                    className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
                  >
                    <RotateCcw className="w-4 h-4" />
                    {t("settings.clear_cache")}
                  </button>
                </div>

                <div className="p-4 bg-gray-50 rounded-xl">
                  <p className="text-sm font-medium text-gray-700 mb-2">{t("settings.storage_used")}</p>
                  <div className="flex items-center gap-3">
                    <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 rounded-full transition-all"
                        style={{ width: `${storageUsed ?? 0}%` }}
                      />
                    </div>
                    <span className="text-sm font-semibold text-gray-900">{storageUsed === null ? "Unavailable" : `${storageUsed}%`}</span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => { const payload = window.localStorage.getItem("glaciernet-kz.preferences") || "{}"; const blob = new Blob([payload], { type: "application/json" }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "glaciernet-kz-browser-preferences.json"; link.click(); URL.revokeObjectURL(url); }}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors"
                >
                  <Database className="w-4 h-4" />
                  Export browser preferences
                </button>
              </div>
            </TabPanel>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-100 flex justify-end">
            <button
              type="button"
              onClick={handleSave}
              className="flex items-center gap-2 px-6 py-2.5 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors"
            >
              <Save className="w-4 h-4" />
              {t("common.save")}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

function FieldGroup({ label, htmlFor, children }: { label: string; htmlFor: string; children: React.ReactNode }) {
  return (
    <div>
      <label htmlFor={htmlFor} className="block text-sm font-medium text-gray-700 mb-1">
        {label}
      </label>
      {children}
    </div>
  );
}

function ToggleRow({ label, checked, onChange, description }: { label: string; checked: boolean; onChange: (v: boolean) => void; description?: string }) {
  return (
    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
      <div>
        <p className="text-sm font-medium text-gray-900">{label}</p>
        {description && <p className="text-xs text-gray-500 mt-0.5">{description}</p>}
      </div>
      <button
        type="button"
        role="switch"
        aria-label={label}
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          checked ? "bg-blue-600" : "bg-gray-300"
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            checked ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
    </div>
  );
}
