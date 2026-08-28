<script type="text/javascript">
$(document).ready(function() {
    function configureInputLimits() {
        var title = document.getElementById('sophosfrontpanel.general.title');
        if (title) {
            title.setAttribute('maxlength', '16');
        }

        [
            ['sophosfrontpanel.general.pollMs', 100, 1000, 10],
            ['sophosfrontpanel.general.refreshSeconds', 2, 60, 1],
            ['sophosfrontpanel.general.rotateSeconds', 2, 60, 1]
        ].forEach(function(item) {
            var field = document.getElementById(item[0]);
            if (field) {
                field.setAttribute('type', 'number');
                field.setAttribute('min', String(item[1]));
                field.setAttribute('max', String(item[2]));
                field.setAttribute('step', String(item[3]));
                field.setAttribute('inputmode', 'numeric');
            }
        });
    }

    function refreshStatus() {
        ajaxCall('/api/sophos_frontpanel/service/status', {}, function(data) {
            $('#frontpanelStatus').text((data && data.status) ? data.status : 'unknown');
        });
    }

    mapDataToFormUI({'frm_GeneralSettings': '/api/sophos_frontpanel/settings/get'}).done(function() {
        configureInputLimits();
        $('.selectpicker').selectpicker('refresh');
        refreshStatus();
    });

    $('#saveAct').click(function() {
        saveFormToEndpoint('/api/sophos_frontpanel/settings/set', 'frm_GeneralSettings', function() {
            ajaxCall('/api/sophos_frontpanel/service/reconfigure', {}, function(data) {
                if (data && data.message) {
                    $('#frontpanelStatus').text(data.message);
                }
                window.setTimeout(refreshStatus, 700);
            });
        });
    });

    $('#checkAct').SimpleActionButton({
        onAction: function(data) {
            if (data && data.message) {
                $('#frontpanelStatus').text(data.message);
            }
            window.setTimeout(refreshStatus, 700);
        }
    });

    $('#restartAct').SimpleActionButton({
        onAction: function(data) {
            if (data && data.message) {
                $('#frontpanelStatus').text(data.message);
            }
            window.setTimeout(refreshStatus, 700);
        }
    });
});
</script>

<div class="content-box">
    {{ partial("layout_partials/base_form", ['fields': generalForm, 'id': 'frm_GeneralSettings']) }}
</div>

<section class="page-content-main">
    <div class="content-box">
        <div class="col-md-12">
            <h4>{{ lang._('Front panel status') }}</h4>
            <pre id="frontpanelStatus" style="white-space:pre-wrap;min-height:3em;">{{ lang._('Loading...') }}</pre>

            <button class="btn btn-primary" id="saveAct" type="button">
                <b>{{ lang._('Save & Apply') }}</b>
            </button>
            <button class="btn btn-default" id="checkAct"
                    data-endpoint="/api/sophos_frontpanel/service/check"
                    data-label="{{ lang._('Check UART') }}"
                    data-error-title="{{ lang._('UART check failed') }}"
                    type="button"></button>
            <button class="btn btn-default" id="restartAct"
                    data-endpoint="/api/sophos_frontpanel/service/restart"
                    data-label="{{ lang._('Restart') }}"
                    data-error-title="{{ lang._('Restart failed') }}"
                    type="button"></button>

            <br/><br/>
            <p><strong>{{ lang._('Buttons:') }}</strong> UP/DOWN = page, ENTER = toggle auto rotation, ESC = home.</p>
            <p><strong>{{ lang._('Serial protocol:') }}</strong> 2400 baud, 8 data bits, no parity, 2 stop bits.</p>
            <p><strong>{{ lang._('Important:') }}</strong> The selected UART must not be used as an OPNsense serial console or by another process.</p>
        </div>
        <div class="clearfix"></div>
    </div>
</section>
