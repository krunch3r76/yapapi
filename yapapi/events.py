"""Representing events in Golem computation.

Events inheritance tree
-----------------------

Notes:

*   Only leaf events are ever emitted, other events (names ending with "Event") are abstract classes
*   Every abstract class has one more `yapapi` object attached then the parent, e.g.

    *   `JobEvent` is an `Event` that is related to a given `yapapi.engine.Job`
    *   `AgreementEvent` is a `JobEvent` that is related to a given `yapapi.rest.market.Agreement`

::

    Event
        JobEvent
            SubscriptionFailed
            SubscriptionEvent
                SubscriptionCreated
                CollectFailed
            ProposalEvent
                ProposalReceived
                ProposalRejected
                ProposalResponded
                ProposalConfirmed
                ProposalFailed
            NoProposalsConfirmed
            ComputationStarted
            ComputationFinished
            AgreementEvent
                AgreementCreated
                AgreementConfirmed
                AgreementRejected
                AgreementTerminated
                ActivityCreateFailed
                WorkerStarted
                ActivityEvent
                    ActivityCreated
                    TaskEvent
                        TaskStarted
                        TaskFinished
                        TaskAccepted
                        TaskRejected
                    ServiceEvent
                        ServiceStarted
                        ServiceFinished
                    ScriptEvent
                        ScriptSent
                        CommandEvent
                            CommandStarted
                            CommandStdOut
                            CommandStdErr
                            CommandExecuted
                            DownloadStarted
                            DownloadFinished
                        GettingResults
                        ScriptFinished
                    WorkerFinished
                InvoiceEvent
                    InvoiceReceived
                    InvoiceAccepted
                DebitNoteEvent
                    DebitNoteReceived
                    DebitNoteAccepted
                PaymentPrepared
                PaymentQueued
                PaymentFailed
        ExecutionInterrupted
        ShutdownFinished
"""

import attr
import abc
from datetime import datetime, timedelta
import logging
from types import TracebackType
from typing import List, Optional, Type, Tuple, TYPE_CHECKING

from yapapi.props import NodeInfo

ExcInfo = Tuple[Type[BaseException], BaseException, Optional[TracebackType]]

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from yapapi.services import Service
    from yapapi.script import Script
    from yapapi.script.command import BatchCommand, Command, _ReceiveContent
    from yapapi.executor.task import Task, TaskData, TaskResult
    from yapapi.rest.activity import Activity
    from yapapi.rest.market import Agreement, OfferProposal, Subscription
    from yapapi.rest.payment import DebitNote, Invoice
    from yapapi.engine import Job


#   ABSTRACT EVENTS
@attr.s
class Event(abc.ABC):
    """An abstract base class for types of events emitted by `Executor.submit()`."""

    exc_info: Optional[ExcInfo] = attr.ib(default=None, kw_only=True)
    """Tuple containing exception info as returned by `sys.exc_info()`, if applicable."""

    @property
    def exception(self) -> Optional[BaseException]:
        """Exception associated with this event or `None` if the event doesn't mean a failure."""
        if self.exc_info:
            return self.exc_info[1]
        return None


@attr.s(auto_attribs=True)
class JobEvent(Event, abc.ABC):
    job: "Job"

    @property
    def job_id(self) -> str:
        return self.job.id

    @property
    def expires(self) -> datetime:
        return self.job.expiration_time

    @property
    def num_offers(self) -> int:
        return self.job.offers_collected


@attr.s(auto_attribs=True)
class SubscriptionEvent(JobEvent, abc.ABC):
    subscription: "Subscription"


@attr.s(auto_attribs=True)
class ProposalEvent(JobEvent, abc.ABC):
    proposal: "OfferProposal"

    @property
    def prop_id(self) -> str:
        return self.proposal.id

    @property
    def provider_id(self) -> str:
        return self.proposal.issuer


@attr.s(auto_attribs=True)
class AgreementEvent(JobEvent, abc.ABC):
    agreement: "Agreement"

    @property
    def agr_id(self) -> str:
        return self.agreement.id

    @property
    def provider_id(self) -> str:
        return self.agreement.cached_details.raw_details.offer.provider_id  # type: ignore

    @property
    def provider_info(self) -> "NodeInfo":
        return self.agreement.cached_details.provider_node_info


@attr.s(auto_attribs=True)
class ActivityEvent(AgreementEvent, abc.ABC):
    activity: "Activity"


@attr.s(auto_attribs=True)
class TaskEvent(ActivityEvent, abc.ABC):
    task: "Task"

    @property
    def task_id(self) -> str:
        return self.task.id

    @property
    def task_data(self) -> "TaskData":
        return self.task.data


@attr.s(auto_attribs=True)
class ServiceEvent(ActivityEvent, abc.ABC):
    service: "Service"


@attr.s(auto_attribs=True)
class ScriptEvent(ActivityEvent, abc.ABC):
    script: "Script"

    @property
    def script_id(self) -> int:
        return self.script.id

    @property
    def cmds(self) -> List["BatchCommand"]:
        #   NOTE: This assumes `script._before()` was already called
        #         (currently this is always true)
        return self.script._evaluate()


@attr.s(auto_attribs=True)
class CommandEvent(ScriptEvent, abc.ABC):
    command: "Command"


@attr.s(auto_attribs=True)
class InvoiceEvent(AgreementEvent, abc.ABC):
    invoice: "Invoice"

    @property
    def amount(self) -> str:
        return self.invoice.amount


@attr.s(auto_attribs=True)
class DebitNoteEvent(AgreementEvent, abc.ABC):
    debit_note: "DebitNote"

    @property
    def amount(self) -> str:
        return self.debit_note.total_amount_due


#   REAL EVENTS
class ComputationStarted(JobEvent):
    pass


class ComputationFinished(JobEvent):
    """Indicates successful completion if `exception` is `None` and a failure otherwise."""


class SubscriptionCreated(SubscriptionEvent):
    pass


@attr.s(auto_attribs=True)
class SubscriptionFailed(JobEvent):
    reason: str


@attr.s(auto_attribs=True)
class CollectFailed(SubscriptionEvent):
    reason: str


class ProposalReceived(ProposalEvent):
    pass


@attr.s(auto_attribs=True)
class ProposalRejected(ProposalEvent):
    reason: Optional[str] = None


class ProposalResponded(ProposalEvent):
    pass


class ProposalConfirmed(ProposalEvent):
    pass


class ProposalFailed(ProposalEvent):
    pass


@attr.s(auto_attribs=True)
class NoProposalsConfirmed(JobEvent):
    timeout: timedelta


class AgreementCreated(AgreementEvent):
    pass


class AgreementConfirmed(AgreementEvent):
    pass


class AgreementRejected(AgreementEvent):
    pass


@attr.s(auto_attribs=True)
class AgreementTerminated(AgreementEvent):
    reason: dict


class DebitNoteReceived(DebitNoteEvent):
    pass


class DebitNoteAccepted(DebitNoteEvent):
    pass


class PaymentPrepared(AgreementEvent):
    pass


class PaymentQueued(AgreementEvent):
    pass


class PaymentFailed(AgreementEvent):
    pass


class InvoiceReceived(InvoiceEvent):
    pass


class InvoiceAccepted(InvoiceEvent):
    pass


class WorkerStarted(AgreementEvent):
    pass


class ActivityCreated(ActivityEvent):
    pass


class ActivityCreateFailed(AgreementEvent):
    pass


class TaskStarted(TaskEvent):
    pass


class TaskFinished(TaskEvent):
    pass


class ServiceStarted(ServiceEvent):
    """Work started for the given service object"""


class ServiceFinished(ServiceEvent):
    """Work finished for the given service object"""


class WorkerFinished(ActivityEvent):
    """Indicates successful completion if `exception` is `None` and a failure otherwise."""


class ScriptSent(ScriptEvent):
    pass


class GettingResults(ScriptEvent):
    pass


class ScriptFinished(ScriptEvent):
    pass


@attr.s(auto_attribs=True)
class CommandExecuted(CommandEvent):
    success: bool
    message: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class CommandStarted(CommandEvent):
    pass


@attr.s(auto_attribs=True)
class CommandStdOut(CommandEvent):
    output: str


@attr.s(auto_attribs=True)
class CommandStdErr(CommandEvent):
    output: str


@attr.s(auto_attribs=True)
class TaskAccepted(TaskEvent):
    @property
    def result(self) -> "TaskResult":
        assert self.task._result is not None
        return self.task._result


@attr.s(auto_attribs=True)
class TaskRejected(TaskEvent):
    reason: Optional[str]


@attr.s(auto_attribs=True)
class DownloadStarted(CommandEvent):
    command: "_ReceiveContent"

    @property
    def path(self) -> str:
        return self.command._src_path


@attr.s(auto_attribs=True)
class DownloadFinished(CommandEvent):
    command: "_ReceiveContent"

    @property
    def path(self) -> str:
        return str(self.command._dst_path)


class ShutdownFinished(Event):
    """Indicates the completion of Executor shutdown sequence"""


class ExecutionInterrupted(Event):
    """Emitted when Golem was stopped by an unhandled exception in code not managed by yapapi"""
