"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { UserPlus, MoreVertical, ChevronDown } from "lucide-react";
import SearchBar from "@/components/SearchBar";
import ConfirmationDialog from "@/components/ConfirmationDialog";
import UserAvatar from "@/components/UserAvatar";
import {
  deleteAdminUser,
  fetchAdminUsers,
  suspendAdminUser,
  updateAdminUserRole,
  type AdminUser,
} from "@/lib/api";

const ROLE_COLORS = {
  admin: "bg-red-50 text-red-700 border-red-200",
  operator: "bg-blue-50 text-blue-700 border-blue-200",
  viewer: "bg-gray-50 text-gray-700 border-gray-200",
};

const STATUS_COLORS = {
  active: "bg-green-50 text-green-700",
  inactive: "bg-gray-100 text-gray-500",
  suspended: "bg-red-50 text-red-700",
};

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [showRoleDropdown, setShowRoleDropdown] = useState<string | null>(null);
  const [confirmAction, setConfirmAction] = useState<{
    type: "role" | "delete" | "suspend";
    user: AdminUser;
  } | null>(null);

  const fetchUsers = useCallback(async () => {
    try {
      setUsers(
        await fetchAdminUsers({
          q: search || undefined,
          role: roleFilter,
          status: statusFilter,
        })
      );
    } catch {
    } finally {
      setLoading(false);
    }
  }, [search, roleFilter, statusFilter]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleRoleChange = useCallback(async (userId: string, newRole: string) => {
    try {
      await updateAdminUserRole(userId, newRole);
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: newRole as AdminUser["role"] } : u))
      );
    } catch {
    }
    setShowRoleDropdown(null);
  }, []);

  const handleSuspend = useCallback(async (userId: string) => {
    try {
      await suspendAdminUser(userId);
      setUsers((prev) =>
        prev.map((u) =>
          u.id === userId
            ? { ...u, status: u.status === "suspended" ? "active" : "suspended" }
            : u
        )
      );
    } catch {
    }
  }, []);

  const handleDelete = useCallback(async (userId: string) => {
    try {
      await deleteAdminUser(userId);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } catch {
    }
  }, []);

  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      !search ||
      u.name.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase());
    const matchesRole = roleFilter === "all" || u.role === roleFilter;
    const matchesStatus = statusFilter === "all" || u.status === statusFilter;
    return matchesSearch && matchesRole && matchesStatus;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Users</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {users.length} total users
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">
          <UserPlus className="w-4 h-4" />
          Add User
        </button>
      </div>

      <div className="flex items-center gap-3">
        <SearchBar
          placeholder="Search users..."
          value={search}
          onChange={setSearch}
          size="sm"
          className="w-64"
        />
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="all">All Roles</option>
          <option value="admin">Admin</option>
          <option value="operator">Operator</option>
          <option value="viewer">Viewer</option>
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="suspended">Suspended</option>
        </select>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50/50">
              <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">User</th>
              <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">Role</th>
              <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">Status</th>
              <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">Datasets</th>
              <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">Predictions</th>
              <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">Last Login</th>
              <th className="w-10 px-4 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b border-gray-50 animate-pulse">
                  <td colSpan={7} className="px-4 py-3">
                    <div className="h-8 bg-gray-100 rounded w-full" />
                  </td>
                </tr>
              ))
            ) : filteredUsers.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-sm text-gray-500">
                  No users found
                </td>
              </tr>
            ) : (
              filteredUsers.map((user) => (
                <tr
                  key={user.id}
                  className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <UserAvatar name={user.name} size="sm" />
                      <div>
                        <p className="text-sm font-medium text-gray-900">{user.name}</p>
                        <p className="text-xs text-gray-500">{user.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 relative">
                    <button
                      onClick={() => setShowRoleDropdown(showRoleDropdown === user.id ? null : user.id)}
                      className={cn(
                        "inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-md border transition-colors",
                        ROLE_COLORS[user.role]
                      )}
                    >
                      {user.role}
                      <ChevronDown className="w-3 h-3" />
                    </button>
                    {showRoleDropdown === user.id && (
                      <div className="absolute left-4 top-full mt-1 w-32 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
                        {(["admin", "operator", "viewer"] as const).map((role) => (
                          <button
                            key={role}
                            onClick={() => handleRoleChange(user.id, role)}
                            className={cn(
                              "block w-full text-left px-3 py-2 text-sm hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg",
                              user.role === role && "bg-blue-50 text-blue-700"
                            )}
                          >
                            {role}
                          </button>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "inline-flex px-2 py-0.5 text-xs font-medium rounded-full",
                        STATUS_COLORS[user.status]
                      )}
                    >
                      {user.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">{user.datasetsCount}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{user.predictionsCount}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {user.lastLogin
                      ? new Date(user.lastLogin).toLocaleDateString()
                      : "Never"}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() =>
                        setConfirmAction({
                          type: user.status === "suspended" ? "suspend" : "delete",
                          user,
                        })
                      }
                      className="p-1 rounded hover:bg-gray-100 text-gray-400"
                    >
                      <MoreVertical className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <ConfirmationDialog
        open={confirmAction?.type === "delete"}
        title="Delete User"
        message={`Are you sure you want to delete ${confirmAction?.user.name}? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        requireConfirmation
        confirmationText="DELETE"
        onConfirm={() => {
          if (confirmAction?.user) handleDelete(confirmAction.user.id);
          setConfirmAction(null);
        }}
        onCancel={() => setConfirmAction(null)}
      />

      <ConfirmationDialog
        open={confirmAction?.type === "suspend"}
        title={confirmAction?.user.status === "suspended" ? "Unsuspend User" : "Suspend User"}
        message={
          confirmAction?.user.status === "suspended"
            ? `Unsuspend ${confirmAction?.user.name}? They will regain access.`
            : `Suspend ${confirmAction?.user.name}? They will lose access.`
        }
        confirmLabel={confirmAction?.user.status === "suspended" ? "Unsuspend" : "Suspend"}
        variant="warning"
        onConfirm={() => {
          if (confirmAction?.user) handleSuspend(confirmAction.user.id);
          setConfirmAction(null);
        }}
        onCancel={() => setConfirmAction(null)}
      />
    </div>
  );
}
