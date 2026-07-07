"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useI18n } from "@/lib/I18nProvider";
import {
  Shield,
  Users,
  ClipboardList,
  Settings,
  Activity,
  ChevronLeft,
  Menu,
  BarChart3,
} from "lucide-react";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { t } = useI18n();
  const [collapsed, setCollapsed] = useState(false);

  const ADMIN_NAV = [
    { href: "/admin", label: t("admin.overview"), icon: BarChart3 },
    { href: "/admin/users", label: t("admin.users"), icon: Users },
    { href: "/admin/audit", label: t("admin.audit"), icon: ClipboardList },
    { href: "/admin/system", label: t("admin.system"), icon: Settings },
  ];

  return (
    <div className="flex min-h-[calc(100vh-4rem)]">
      <aside
        className={cn(
          "border-r border-gray-200 bg-white transition-all duration-200 flex flex-col",
          collapsed ? "w-16" : "w-56"
        )}
      >
        <div className="flex items-center justify-between px-3 py-3 border-b border-gray-100">
          {!collapsed && (
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-semibold text-gray-900">{t("admin.title")}</span>
            </div>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1.5 rounded-md hover:bg-gray-100 text-gray-500"
            aria-label={collapsed ? t("common.show") : t("common.hide")}
          >
            {collapsed ? <Menu className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        <nav className="flex-1 py-2 px-2 space-y-0.5">
          {ADMIN_NAV.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-colors",
                  isActive
                    ? "bg-blue-50 text-blue-700 font-medium"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                )}
                title={collapsed ? item.label : undefined}
              >
                <item.icon className="w-4 h-4 flex-shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {!collapsed && (
          <div className="p-3 border-t border-gray-100">
            <div className="flex items-center gap-2 px-2 py-1.5 bg-amber-50 rounded-lg">
              <Activity className="w-3.5 h-3.5 text-amber-600" />
              <span className="text-[10px] text-amber-700">{t("admin.access_badge")}</span>
            </div>
          </div>
        )}
      </aside>

      <main className="flex-1 overflow-y-auto bg-gray-50/50 p-6">{children}</main>
    </div>
  );
}
