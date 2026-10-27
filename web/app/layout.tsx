import "./style.css";
import type { Metadata } from "next";
export const metadata: Metadata = {
  title: "Brasil do Futuro | Observatório",
  description: "Fundação auditável de inteligência econômica independente.",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
