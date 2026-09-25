import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { displayProgress, percentFromStep, scanProgressFromSteps } from "./progress-ui";
import { SCAN_STEPS, statusesForScan } from "./steps";

function progressAtPipelineStep(currentStep: number, apiProgress = 75) {
  const activity = SCAN_STEPS[currentStep - 1]?.activity ?? "Validating website";
  const steps = statusesForScan({
    progress: apiProgress,
    currentStep: activity,
    status: "running",
  });
  return scanProgressFromSteps(steps);
}

function stepLabel(currentStep: number, totalSteps: number) {
  return `Step ${currentStep} of ${totalSteps}`;
}

describe("scan progress source of truth", () => {
  const totalSteps = SCAN_STEPS.length;

  it("matches the circle percent to Step X of Y for every pipeline step", () => {
    for (let currentStep = 1; currentStep <= totalSteps; currentStep++) {
      const shown = progressAtPipelineStep(currentStep, 75);
      const expectedPercent = Math.round((currentStep / totalSteps) * 100);

      assert.equal(shown.currentStep, currentStep);
      assert.equal(shown.totalSteps, totalSteps);
      assert.equal(shown.percent, expectedPercent);
      assert.equal(shown.percent, percentFromStep(shown.currentStep, shown.totalSteps));
      assert.equal(stepLabel(shown.currentStep, shown.totalSteps), stepLabel(currentStep, totalSteps));
    }
  });

  it("keeps the circle in sync with the step text at start, mid-scan, and last step", () => {
    for (const currentStep of [1, 8, Math.ceil(totalSteps / 2), totalSteps]) {
      const shown = progressAtPipelineStep(currentStep, 99);
      const expectedPercent = Math.round((currentStep / totalSteps) * 100);
      assert.equal(shown.percent, expectedPercent);
      assert.equal(stepLabel(shown.currentStep, shown.totalSteps), stepLabel(currentStep, totalSteps));
    }
  });

  it("ignores weighted API progress so Rendering is 8 of 21, not 75%", () => {
    const shown = progressAtPipelineStep(8, 75);
    assert.equal(shown.currentStep, 8);
    assert.equal(shown.totalSteps, 21);
    assert.equal(shown.percent, Math.round((8 / 21) * 100));
    assert.notEqual(shown.percent, 75);
    assert.equal(displayProgress(75, statusesForScan({
      progress: 75,
      currentStep: "Rendering website",
      status: "running",
    })), shown.percent);
  });

  it("reaches 100% only when currentStep equals totalSteps", () => {
    for (let currentStep = 1; currentStep <= totalSteps; currentStep++) {
      const shown = progressAtPipelineStep(currentStep);
      if (currentStep === totalSteps) {
        assert.equal(shown.percent, 100);
      } else {
        assert.notEqual(shown.percent, 100);
      }
    }
  });

  it("shows 100% on Finalizing completion, not from API progress alone", () => {
    const complete = scanProgressFromSteps(
      statusesForScan({
        progress: 100,
        currentStep: "Analysis complete",
        status: "completed",
      }),
    );
    assert.equal(complete.currentStep, totalSteps);
    assert.equal(complete.totalSteps, totalSteps);
    assert.equal(complete.percent, 100);

    const almostDone = progressAtPipelineStep(totalSteps - 1, 100);
    assert.equal(almostDone.currentStep, totalSteps - 1);
    assert.notEqual(almostDone.percent, 100);
  });

  it("interpolates optional sub-step progress without changing Step X of Y", () => {
    const steps = statusesForScan({
      progress: 75,
      currentStep: "Rendering website",
      status: "running",
    });
    const shown = scanProgressFromSteps(steps, 0.5);
    assert.equal(shown.currentStep, 8);
    assert.equal(shown.totalSteps, 21);
    assert.equal(shown.percent, Math.round(((8 - 1 + 0.5) / 21) * 100));
    assert.equal(stepLabel(shown.currentStep, shown.totalSteps), "Step 8 of 21");
  });
});
