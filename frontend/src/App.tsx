import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./lib/auth";
import AppShell from "./components/AppShell";
import Login from "./pages/Login";
import Join from "./pages/Join";
import Dashboard from "./pages/Dashboard";
import Onboarding from "./pages/Onboarding";
import Peers from "./pages/Peers";
import Week from "./pages/Week";
import Bundles from "./pages/Bundles";
import Voice from "./pages/Voice";
import Showcase from "./pages/Showcase";
import Goals from "./pages/Goals";
import Ledger from "./pages/Ledger";
import Badges from "./pages/Badges";
import Missions from "./pages/Missions";
import Rewards from "./pages/Rewards";
import Requests from "./pages/Requests";
import Recommendations from "./pages/Recommendations";
import Privacy from "./pages/Privacy";
import Cases from "./pages/Cases";
import Approvals, { Advisees, ReviewCases, AppealsQueue } from "./pages/Workflows";
import { AdminOverview, AdminPolicies, AdminCatalog, AdminHealth, PolicyApprovals } from "./pages/Admin";
import SsoSettingsPage from "./pages/SsoSettings";
import { Provider, Audit, Tech } from "./pages/RolePages";
import SmartAssistant from "./components/SmartAssistant";

function Protected() {
  const { me, loading } = useAuth();
  if (loading) return <div className="flex min-h-screen items-center justify-center text-ink-soft">…</div>;
  if (!me) return <Navigate to="/login" replace />;
  return <AppShell />;
}

/** Route-level RBAC mirror: server stays the authority; this only avoids confusing empty pages. */
function RequirePerm({ perm, children }: { perm: string; children: React.ReactNode }) {
  const { me } = useAuth();
  if (!me) return <Navigate to="/login" replace />;
  if (!me.permissions.includes(perm)) return <Navigate to="/" replace />;
  return <>{children}</>;
}

/** Route-level role gate (multiple allowed roles) — server stays the authority. */
function RequireRoles({ roles, children }: { roles: string[]; children: React.ReactNode }) {
  const { me } = useAuth();
  if (!me) return <Navigate to="/login" replace />;
  if (!roles.some((r) => me.roles.includes(r))) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <>
      {/* دستیار هوشمند «دانشگاه هوشمند من» — در همهٔ صفحات، پایین‌چپ (v1.6) */}
      <SmartAssistant />
      <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Protected />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/join" element={<Join />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/peers" element={<RequirePerm perm="ledger:read_own">{<Peers />}</RequirePerm>} />
        <Route path="/week" element={<RequirePerm perm="ledger:read_own">{<Week />}</RequirePerm>} />
        <Route path="/bundles" element={<RequirePerm perm="ledger:read_own">{<Bundles />}</RequirePerm>} />
        <Route path="/voice" element={<RequirePerm perm="ledger:read_own">{<Voice />}</RequirePerm>} />
        <Route path="/showcase" element={<Showcase />} />
        <Route path="/goals" element={<Goals />} />
        <Route path="/ledger" element={<Ledger />} />
        <Route path="/badges" element={<Badges />} />
        <Route path="/missions" element={<Missions />} />
        <Route path="/rewards" element={<Rewards />} />
        <Route path="/requests" element={<Requests />} />
        <Route path="/recommendations" element={<Recommendations />} />
        <Route path="/cases" element={<Cases />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/approvals" element={<RequirePerm perm="approvals:verify">{<Approvals />}</RequirePerm>} />
        <Route path="/advisees" element={<RequirePerm perm="advisor:read">{<Advisees />}</RequirePerm>} />
        <Route path="/review-cases" element={<RequirePerm perm="reviews:handle">{<ReviewCases />}</RequirePerm>} />
        <Route path="/appeals-queue" element={<RequirePerm perm="appeals:review">{<AppealsQueue />}</RequirePerm>} />
        <Route path="/admin" element={<RequirePerm perm="analytics:read">{<AdminOverview />}</RequirePerm>} />
        <Route path="/admin/policies" element={<RequirePerm perm="policies:read">{<AdminPolicies />}</RequirePerm>} />
        <Route path="/admin/catalog" element={<RequirePerm perm="rewards:manage">{<AdminCatalog />}</RequirePerm>} />
        <Route path="/admin/health" element={<RequirePerm perm="events:manage">{<AdminHealth />}</RequirePerm>} />
        <Route path="/admin/sso" element={<RequireRoles roles={["club_manager", "tech_admin"]}>{<SsoSettingsPage />}</RequireRoles>} />
        <Route path="/policy-approvals" element={<RequirePerm perm="policies:approve">{<PolicyApprovals />}</RequirePerm>} />
        <Route path="/provider" element={<RequirePerm perm="rewards:deliver">{<Provider />}</RequirePerm>} />
        <Route path="/audit" element={<RequirePerm perm="audit:read">{<Audit />}</RequirePerm>} />
        <Route path="/tech" element={<RequirePerm perm="tech:admin">{<Tech />}</RequirePerm>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
