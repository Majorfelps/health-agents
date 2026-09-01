import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Health Agents — ED o Nutri & ED o Personal",
  description: "Dashboard + chat com agentes de nutri e treino",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
