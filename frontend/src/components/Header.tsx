import { useAuth } from "../context/AuthContext";
import { NavBar } from "./NavBar";
import { ThemeToggle } from "./ThemeToggle";
import { ProfileMenu } from "./ProfileMenu";

export function Header() {
  const { identity } = useAuth();

  return (
    <>
      <header className="flex items-center justify-between border-b border-surface-border px-6 py-4">
        <div className="flex items-center gap-2">
          <span className="text-xl">🎟️</span>
          <span className="text-lg font-bold text-ink">TickTrack</span>
        </div>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          {identity && <ProfileMenu />}
        </div>
      </header>
      <NavBar />
    </>
  );
}
