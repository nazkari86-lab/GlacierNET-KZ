// GlacierNET-KZ Settings Page
"use client";

import { useState } from "react";
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
  const [apiUrl, setApiUrl] = useState("http://localhost:8000");
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
  const [apiKeyVisible, setApiKeyVisible] = useState(false);
  const apiKey = "gkz-••••••••••••••••••••••••";
  const [sessionTimeout, setSessionTimeout] = useState("60");
  const [mfaEnabled, setMfaEnabled] = useState(false);

  // Data Management
  const [cacheSize] = useState(256);
  const [storageUsed] = useState(42);

  const handleSave = () => {
    setLocale(selectedLang);
    toast.success(t("settings.save_success"));
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
                <FieldGroup label="API Base URL" htmlFor="api-url">
                  <input
                    id="api-url"
                    type="url"
                    value={apiUrl}
                    onChange={(e) => setApiUrl(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    placeholder="http://localhost:8000"
                  />
                </FieldGroup>

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
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("settings.api_key")}</label>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 bg-gray-100 rounded-lg px-3 py-2 text-sm font-mono text-gray-700">
                      {apiKeyVisible ? "gkz-a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5" : apiKey}
                    </code>
                    <button
                      type="button"
                      onClick={() => setApiKeyVisible(!apiKeyVisible)}
                      className="px-3 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
                    >
                      {apiKeyVisible ? t("common.hide") : t("common.show")}
                    </button>
                  </div>
                </div>

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
                    <p className="text-2xl font-bold text-gray-900 mt-1">{cacheSize} MB</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => toast.info(t("settings.clear_cache"))}
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
                        style={{ width: `${storageUsed}%` }}
                      />
                    </div>
                    <span className="text-sm font-semibold text-gray-900">{storageUsed}%</span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => toast.success("Export started")}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors"
                >
                  <Database className="w-4 h-4" />
                  Export All Data
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
