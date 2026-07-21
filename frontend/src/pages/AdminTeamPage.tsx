import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminCreateAdmin, adminDeleteAdmin, adminListAdmins } from "../api/client";
import { ASSIGNED_TEAMS } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/Button";
import { Card, CardLabel } from "../components/ui/Card";
import { ErrorBanner, ErrorMessage, Spinner, SuccessBanner } from "../components/ui/Feedback";
import { SelectField, TextField } from "../components/ui/FormField";
import { Modal } from "../components/ui/Modal";

export function AdminTeamPage() {
  const { token, identity } = useAuth();
  const queryClient = useQueryClient();
  const isSuperAdmin = identity?.department == null;

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [department, setDepartment] = useState("");
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);
  const [justDeletedName, setJustDeletedName] = useState("");

  const { data: admins, isLoading, error } = useQuery({
    queryKey: ["admin-admins"],
    queryFn: () => adminListAdmins(token!),
    enabled: !!token,
  });

  const createMutation = useMutation({
    mutationFn: () => adminCreateAdmin(token!, name, email, password, department || undefined),
    onSuccess: () => {
      setName("");
      setEmail("");
      setPassword("");
      setDepartment("");
      queryClient.invalidateQueries({ queryKey: ["admin-admins"] });
    },
  });

  const deleteTarget = admins?.find((a) => a.id === deleteTargetId) ?? null;

  const deleteMutation = useMutation({
    mutationFn: (id: number) => adminDeleteAdmin(token!, id),
    onSuccess: () => {
      setJustDeletedName(deleteTarget?.name ?? "");
      setDeleteTargetId(null);
      queryClient.invalidateQueries({ queryKey: ["admin-admins"] });
    },
  });

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-6 py-8">
      <Link to="/admin" className="text-sm text-ink-muted hover:text-ink">
        ← Back to Dashboard
      </Link>

      <h1 className="text-2xl font-bold text-ink">Manage Team</h1>

      {!isSuperAdmin ? (
        <ErrorBanner message="Only super-admins can manage team accounts." />
      ) : (
        <>
          <Card className="space-y-3">
            <CardLabel>Create a team account</CardLabel>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <TextField label="Name" value={name} onChange={(e) => setName(e.target.value)} />
              <TextField
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <TextField
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <SelectField
                label="Department"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
              >
                <option value="">— none (super-admin) —</option>
                {ASSIGNED_TEAMS.map((team) => (
                  <option key={team} value={team}>
                    {team}
                  </option>
                ))}
              </SelectField>
            </div>
            <Button
              variant="primary"
              disabled={!name || !email || !password || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              {createMutation.isPending ? "Creating…" : "Create Account"}
            </Button>
            {createMutation.isError && (
              <ErrorBanner message={ErrorMessage(createMutation.error)} />
            )}
            {createMutation.isSuccess && (
              <SuccessBanner message={`Created ${createMutation.data.name} <${createMutation.data.email}>.`} />
            )}
          </Card>

          <Card className="space-y-3">
            <CardLabel>Existing team accounts</CardLabel>
            {isLoading && <Spinner label="Loading team accounts…" />}
            {error && <ErrorBanner message={ErrorMessage(error)} />}
            {justDeletedName && <SuccessBanner message={`Removed ${justDeletedName}.`} />}
            {admins && (
              <div className="space-y-2">
                {admins.map((admin) => (
                  <div
                    key={admin.id}
                    className="flex items-center justify-between rounded-md border border-surface-border px-3 py-2 text-sm"
                  >
                    <div>
                      <p className="text-ink">{admin.name}</p>
                      <p className="text-ink-muted">{admin.email}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-ink-muted">{admin.department ?? "super-admin"}</span>
                      <Button
                        variant="danger"
                        disabled={admin.id === identity?.id}
                        onClick={() => setDeleteTargetId(admin.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </>
      )}

      {deleteTarget && (
        <Modal title="Delete team account" onClose={() => setDeleteTargetId(null)}>
          <p className="text-sm text-ink-muted">
            Permanently delete <strong className="text-ink">{deleteTarget.name}</strong> (
            {deleteTarget.email})? Any tickets assigned to them will become unassigned. This
            cannot be undone.
          </p>
          {deleteMutation.isError && <ErrorBanner message={ErrorMessage(deleteMutation.error)} />}
          <div className="mt-4 flex justify-end gap-2">
            <Button onClick={() => setDeleteTargetId(null)}>Cancel</Button>
            <Button
              variant="danger"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate(deleteTarget.id)}
            >
              Delete Permanently
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
}
