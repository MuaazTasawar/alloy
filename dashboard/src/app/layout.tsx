import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Alloy — LLM Ops Dashboard",
  description:
    "Route queries between RAG, a fine-tuned model, and the base model — and see which one wins.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-neutral-950 font-sans antialiased">
        {children}
      </body>
    </html>
  );
}