import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CurriculumAI",
  description:
    "A curriculum planner whose agents learn a professor's teaching style from what they choose.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
