---
tags:
  - monitoring
---

# CloudWatch Dashboard with Metric Graphs, Alarm Status, and Text Widgets

A CloudWatch dashboard built with CDK widget classes — no hand-crafted dashboard JSON required.

## Code

```python
from aws_cdk import (
    Stack,
    aws_cloudwatch as cw,
)
from constructs import Construct


class DashboardStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        dashboard = cw.Dashboard(
            self,
            "AppDashboard",
            dashboard_name="App-Prod",
        )

        dashboard.add_widgets(
            cw.GraphWidget(
                title="Queue Depth",
                left=[queue.metric_approximate_number_of_messages_visible()],
            ),
            cw.AlarmStatusWidget(
                alarms=[alarm],
                title="Active Alarms",
            ),
            cw.SingleValueWidget(
                metrics=[latency_metric],
                title="p99 Latency",
            ),
            cw.TextWidget(
                markdown="# Production Dashboard\nAuto-generated from CDK.",
            ),
        )
```

## What's Happening

- **`Dashboard` (L2)** writes the entire dashboard JSON body. You never craft `AWS::CloudWatch::Dashboard` DashboardBody JSON manually — CDK serializes the widget tree during synthesis.

- **Widget classes** are CDK constructs (not CloudFormation resources individually):
  - `GraphWidget` — time-series metric graph with optional `left`/`right` axes. CDK renders both Y-axes in the dashboard JSON.
  - `AlarmStatusWidget` — shows current state of one or more alarms. Updates in real-time on the dashboard.
  - `SingleValueWidget` — displays the latest value of a metric with optional trend sparkline.
  - `TextWidget` — renders Markdown for headings, descriptions, links.

- **`add_widgets()`** places widgets in a single column by default (one widget per row). Pass a list of lists (`widgets=[[...]]`) for multi-column layouts, where each inner list is a row of widgets.

- **`period` and `stat` are inherited from the `Metric` objects** passed to the widgets, but widgets can override rendering. For example, `GraphWidget(..., left_annotations=[...])` adds horizontal annotation lines to the graph.

- **`Dashboard` name** is set via `dashboard_name`. Without it, CloudFormation generates a name. The dashboard resource is purely a CloudFormation configuration resource — it does not retain state or require IAM permissions to create.

### Key CDK Concepts

- `cw.Dashboard` creates a single `AWS::CloudWatch::Dashboard` resource. The widgets are synthesized into the `DashboardBody` JSON property — they are not separate CloudFormation resources.
- `Metric` objects used in widgets respect the metric identity (namespace, metric name, dimensions, stat, period) defined when the metric was created. Widgets can override stat and period via the widget constructor.
- `TextWidget` markdown is embedded in the dashboard JSON as a `markdown` property. There is no separate rendering step.
- Dashboard JSON is a CDK token — it is resolved during synthesis. Large dashboards with many widgets synthesize into a single CloudFormation template property.

## Cross-Refs

See [[cloudwatch-alarms]] for creating the alarms referenced in `AlarmStatusWidget`.
