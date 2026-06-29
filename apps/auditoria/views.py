import csv
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.http import HttpResponse, StreamingHttpResponse
from django.contrib.auth.decorators import login_required
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from .models import AuditLog


class AuditLogListView(LoginRequiredMixin, ListView):
    model = AuditLog
    template_name = "auditoria/auditlog_list.html"
    context_object_name = "logs"
    paginate_by = 30

    def get_queryset(self):
        qs = AuditLog.objects.select_related("usuario").order_by("-timestamp")
        evento = self.request.GET.get("evento")
        q = self.request.GET.get("q")
        if evento:
            qs = qs.filter(evento=evento)
        if q:
            qs = qs.filter(usuario__email__icontains=q) | qs.filter(ip_address__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["eventos"] = AuditLog.Evento.choices
        return ctx


auditlog_list = AuditLogListView.as_view()


class Echo:
    def write(self, value):
        return value


@login_required
def exportar_auditoria_csv(request):
    qs = AuditLog.objects.select_related("usuario").order_by("-timestamp")
    evento = request.GET.get("evento")
    if evento:
        qs = qs.filter(evento=evento)
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    writer.writerow(["Evento", "Usuario", "IP", "Datos", "Fecha"])
    for log in qs:
        writer.writerow([log.evento, str(log.usuario or ""), log.ip_address, str(log.datos), str(log.timestamp)])
    return StreamingHttpResponse(
        (pseudo_buffer.write for _ in range(1)),
        content_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="auditoria.csv"'},
    )


@login_required
def exportar_auditoria_excel(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Auditoría"
    ws.append(["Evento", "Usuario", "IP", "Datos", "Fecha"])
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="1D4ED8", end_color="1D4ED8", fill_type="solid")
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
    qs = AuditLog.objects.select_related("usuario").order_by("-timestamp")
    evento = request.GET.get("evento")
    if evento:
        qs = qs.filter(evento=evento)
    for log in qs:
        ws.append([log.evento, str(log.usuario or ""), log.ip_address, str(log.datos), str(log.timestamp)])
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="auditoria.xlsx"'
    wb.save(response)
    return response
