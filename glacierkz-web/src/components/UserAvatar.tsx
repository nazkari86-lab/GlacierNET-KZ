"use client";

/* eslint-disable @next/next/no-img-element -- avatars may be arbitrary runtime URLs with error fallback. */

import { useState, useCallback } from "react";
import { cn } from "@/lib/utils";

interface UserAvatarProps {
  name?: string;
  src?: string;
  email?: string;
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  showStatus?: boolean;
  status?: "online" | "offline" | "away" | "busy";
  onClick?: () => void;
  className?: string;
  showTooltip?: boolean;
}

const SIZE_MAP = {
  xs: "w-6 h-6 text-[10px]",
  sm: "w-8 h-8 text-xs",
  md: "w-10 h-10 text-sm",
  lg: "w-14 h-14 text-lg",
  xl: "w-20 h-20 text-2xl",
};

const STATUS_COLOR: Record<string, string> = {
  online: "bg-green-500",
  offline: "bg-gray-400",
  away: "bg-amber-500",
  busy: "bg-red-500",
};

const AVATAR_COLORS = [
  "bg-blue-500",
  "bg-green-500",
  "bg-purple-500",
  "bg-amber-500",
  "bg-teal-500",
  "bg-rose-500",
  "bg-indigo-500",
  "bg-cyan-500",
];

function getInitials(name?: string): string {
  if (!name) return "?";
  return name
    .split(" ")
    .map((w) => w[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function getColorByName(name?: string): string {
  if (!name) return AVATAR_COLORS[0];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

export default function UserAvatar({
  name,
  src,
  email,
  size = "md",
  showStatus = false,
  status = "offline",
  onClick,
  className,
  showTooltip = true,
}: UserAvatarProps) {
  const [imgError, setImgError] = useState(false);
  const [showTooltipState, setShowTooltipState] = useState(false);

  const initials = getInitials(name);
  const bgColor = getColorByName(name);

  const handleImageError = useCallback(() => setImgError(true), []);

  return (
    <div
      className={cn("relative inline-flex", onClick && "cursor-pointer", className)}
      onMouseEnter={() => setShowTooltipState(true)}
      onMouseLeave={() => setShowTooltipState(false)}
      onClick={onClick}
    >
      <div className={cn("rounded-full flex items-center justify-center font-medium text-white overflow-hidden", SIZE_MAP[size])}>
        {src && !imgError ? (
          <img
            src={src}
            alt={name || "User"}
            className="w-full h-full object-cover"
            onError={handleImageError}
          />
        ) : (
          <div className={cn("w-full h-full flex items-center justify-center", bgColor)}>
            {initials}
          </div>
        )}
      </div>

      {showStatus && (
        <span
          className={cn(
            "absolute bottom-0 right-0 rounded-full border-2 border-white",
            STATUS_COLOR[status],
            size === "xs" || size === "sm" ? "w-2 h-2" : "w-3 h-3"
          )}
        />
      )}

      {showTooltip && showTooltipState && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-white text-[10px] rounded whitespace-nowrap z-50">
          {name || "Unknown"}
          {email && <div className="text-gray-400">{email}</div>}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
        </div>
      )}
    </div>
  );
}

interface UserAvatarGroupProps {
  users: Array<{ name?: string; src?: string; email?: string }>;
  max?: number;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function UserAvatarGroup({ users, max = 3, size = "sm", className }: UserAvatarGroupProps) {
  const visible = users.slice(0, max);
  const remaining = users.length - max;

  return (
    <div className={cn("flex items-center", className)}>
      {visible.map((user, i) => (
        <div key={i} className={cn("-ml-1.5 first:ml-0")}>
          <UserAvatar {...user} size={size} showTooltip />
        </div>
      ))}
      {remaining > 0 && (
        <div
          className={cn(
            "-ml-1.5 rounded-full bg-gray-200 flex items-center justify-center font-medium text-gray-600",
            size === "sm" ? "w-8 h-8 text-[10px]" : size === "md" ? "w-10 h-10 text-xs" : "w-14 h-14 text-sm"
          )}
        >
          +{remaining}
        </div>
      )}
    </div>
  );
}

export type { UserAvatarProps, UserAvatarGroupProps };
