import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Atlas — Your company, connected.",
  description:
    "A secure home for company knowledge. Ask questions across your documents and get answers with evidence.",
  robots: { index: true, follow: true },
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
