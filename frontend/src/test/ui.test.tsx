import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState, Button, Chip } from "../components/ui";
import { formatPoints, formatJalali, toFa } from "../lib/format";

describe("UI kit", () => {
  it("renders EmptyState with Persian text", () => {
    render(<EmptyState title="هنوز تراکنشی ثبت نشده" body="با تکمیل فعالیت‌ها امتیاز دیده می‌شود." />);
    expect(screen.getByText("هنوز تراکنشی ثبت نشده")).toBeInTheDocument();
  });
  it("Button is keyboard-accessible with label", () => {
    render(<Button>درخواست پاداش</Button>);
    const btn = screen.getByRole("button", { name: "درخواست پاداش" });
    expect(btn).toBeInTheDocument();
    btn.focus();
    expect(btn).toHaveFocus();
  });
  it("Chip renders", () => {
    render(<Chip tone="ok">تحویل‌شده</Chip>);
    expect(screen.getByText("تحویل‌شده")).toBeInTheDocument();
  });
});

describe("formatting", () => {
  it("converts digits to Persian", () => {
    expect(toFa("123")).toBe("۱۲۳");
  });
  it("formats points with 2 decimals", () => {
    expect(formatPoints("24.5")).toBe(toFa("24.50"));
  });
  it("formats Jalali date (Persian calendar)", () => {
    const s = formatJalali("2026-11-11T00:00:00Z");
    expect(s).toMatch(/[۰-۹]/); // contains Persian digits
  });
});
