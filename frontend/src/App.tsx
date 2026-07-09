import { useState } from "react";
import { DemoPage } from "./pages/DemoPage";
import { HomePage } from "./pages/HomePage";

type View = "home" | "demo";

export default function App() {
  const [view, setView] = useState<View>("home");

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 p-4">
      {view === "home" ? (
        <HomePage onNavigateToDemo={() => setView("demo")} />
      ) : (
        <DemoPage onNavigateHome={() => setView("home")} />
      )}
    </div>
  );
}
