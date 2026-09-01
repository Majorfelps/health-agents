"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Dashboard", icon: "📊" },
  { href: "/chat", label: "Chat", icon: "💬" },
  { href: "/plan", label: "Planos", icon: "📋" },
  { href: "/checkins", label: "Check-ins", icon: "✅" },
  { href: "/settings", label: "IA", icon: "🤖" },
];

export default function NavBar() {
  const path = usePathname();
  return (
    <nav className="bg-wa-green-dark text-white">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-6">
        <Link href="/" className="font-bold text-lg flex items-center gap-2">
          <span>🥗</span>
          <span>Health Agents</span>
        </Link>
        <div className="flex-1" />
        <ul className="flex gap-1">
          {NAV.map((n) => {
            const active = path === n.href;
            return (
              <li key={n.href}>
                <Link
                  href={n.href}
                  className={
                    "px-3 py-1.5 rounded-lg text-sm flex items-center gap-1.5 transition " +
                    (active ? "bg-white/15 font-semibold" : "hover:bg-white/10")
                  }
                >
                  <span>{n.icon}</span>
                  <span>{n.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </nav>
  );
}
