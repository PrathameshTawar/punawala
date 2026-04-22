import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import ExplainPanel from "./ExplainPanel";

const APPROVED_DECISION = {
  status: "Approved",
  reasons_pass: ["Verbal consent confirmed", "Income ₹50,000 meets threshold"],
  reasons_fail: [],
  confidence: 0.87,
  credit_score_band: "A",
  model_version: "risk-engine-v2.1",
};

const REJECTED_DECISION = {
  status: "Rejected",
  reasons_pass: ["Verbal consent confirmed"],
  reasons_fail: ["Income ₹10,000 below minimum ₹25,000"],
  confidence: 0.12,
  credit_score_band: null,
  model_version: "risk-engine-v2.1",
};

test("renders nothing when decision is null", () => {
  const { container } = render(<ExplainPanel decision={null} />);
  expect(container).toBeEmptyDOMElement();
});

test("shows all passing reasons with checkmarks", () => {
  render(<ExplainPanel decision={APPROVED_DECISION} />);
  expect(screen.getByText("Verbal consent confirmed")).toBeInTheDocument();
  expect(screen.getByText("Income ₹50,000 meets threshold")).toBeInTheDocument();
});

test("shows failing reasons with X marks", () => {
  render(<ExplainPanel decision={REJECTED_DECISION} />);
  expect(screen.getByText(/income.*below minimum/i)).toBeInTheDocument();
});

test("shows confidence percentage", () => {
  render(<ExplainPanel decision={APPROVED_DECISION} />);
  expect(screen.getByText("87%")).toBeInTheDocument();
});

test("shows credit band", () => {
  render(<ExplainPanel decision={APPROVED_DECISION} />);
  expect(screen.getByText("A")).toBeInTheDocument();
});

test("shows model version", () => {
  render(<ExplainPanel decision={APPROVED_DECISION} />);
  expect(screen.getByText("risk-engine-v2.1")).toBeInTheDocument();
});

test("does not show credit band when null", () => {
  render(<ExplainPanel decision={REJECTED_DECISION} />);
  // credit_score_band is null — should not render "A", "B", etc.
  expect(screen.queryByText(/^[ABCD]$/)).not.toBeInTheDocument();
});
