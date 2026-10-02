// soctime.js – interaction layer for the SocTime timeline chart.
// One copy of this file serves every page. Build-time configuration is injected
// by SocTime.R before widget init as:
//   window.SocTimeConfig = {
//     labelCutoffYear, tickIntervalMs, infoTitle, infoText,
//     periodId, periodLabel, prevHref, prevLabel, nextHref, nextLabel,
//     indexHref,
//     portraitPx, traditions
//   }
// labelCutoffYear is null on a period page: only the full-span page suppresses
// the labels of its opening gutter. periodLabel is null there in turn, and the
// navigation strip is then not built. traditions is the list of
// { id, label } pairs that the highlight selector offers, in vocabulary order
// and limited to the traditions somebody on the page carries; an empty list
// means no selector.
//
// A query string of the form ?from=1700&to=1760 zooms the x-axis to those
// years once the chart has loaded. It exists so that a zoomed state can be
// screenshotted from a headless browser; readers zoom by dragging.

window.SocTime = (function () {

  // ===== Close button helper =====
  function createCloseButton(overlay) {
    const btn = document.createElement('button');
    btn.textContent = '×';
    btn.style.cssText = `
      display: inline-block;
      border: none;
      background: none;
      font-size: 28px;
      font-weight: bold;
      cursor: pointer;
      color: #333;
      transform-origin: center center;
      transition: color 0.3s ease, transform 0.3s ease;
    `;
    btn.onmouseover = function() {
      this.style.color = '#d4af37';
      this.style.transform = 'rotate(90deg)';
    };
    btn.onmouseout = function() {
      this.style.color = '#333';
      this.style.transform = 'rotate(0deg)';
    };
    btn.onclick = function() { overlay.remove(); };
    return btn;
  }

  // ===== Info icon + overlay =====
  function addInfoIconOverlay(chart) {
    const info_title = window.SocTimeConfig.infoTitle;
    const info_text = window.SocTimeConfig.infoText;

    if (document.getElementById('chartInfoIcon')) return;
    const info = document.createElement('div');
    info.id = 'chartInfoIcon';
    info.textContent = 'i';
    info.style.cssText = `
      position: absolute;
      top: 9px;
      left: 10px;
      width: 22px;
      height: 22px;
      border-radius: 50%;
      background-color: #ffffff;
      border: 2px solid #000000ff;
      color: #000000ff;
      font-weight: bold;
      font-size: 22px;
      text-align: center;
      line-height: 23px;
      cursor: pointer;
      z-index: 9998;
      transition: all 0.2s ease;
      font-family: Arial, sans-serif;
    `;
    info.onmouseover = function() {
      this.style.backgroundColor = '#d4af37';
      this.style.borderColor = '#d4af37';
      this.style.color = '#ffffff';
      tooltip.style.opacity = 1;
    };
    info.onmouseout = function() {
      this.style.backgroundColor = '#ffffff';
      this.style.borderColor = '#000000ff';
      this.style.color = '#000000ff';
      tooltip.style.opacity = 0;
    };
    // Pop-up box
    info.onclick = function() {
      // Remove any existing overlay first
      const existing = document.getElementById('chartInfoOverlay');
      if (existing) existing.remove();

      // Overlay container
      const overlay = document.createElement('div');
      overlay.id = 'chartInfoOverlay';
      overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        z-index: 9999;
        display: flex;
        align-items: flex-start;
        justify-content: flex-start;
        padding-top: 10px;
        padding-left: 40px;
      `;

      // Dialog box
      const dialog = document.createElement('div');
      dialog.style.cssText = `
        background: rgba(250,250,250,0.8);
        padding: 10px 15px 10px 15px;
        border-radius: 5px;
        max-width: 50%;
        max-height: 90%;
        overflow-y: auto;
        box-shadow: 0 8px 16px rgba(0,0,0,0.4);
        text-align: justify;
        font-family: Arial, sans-serif;
        font-size: 14px;
        animation: slideIn 0.3s ease-out;
      `;
      overlay.appendChild(dialog);

      // Pop-up box: header
      const header = document.createElement('div');
      header.style.cssText = `
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
        font-size: 16px;
      `;
      dialog.appendChild(header);

      // Pop-up box: title
      const title = document.createElement('h4');
      title.textContent = info_title;
      title.style.margin = '0';
      header.appendChild(title);

      // Pop-up box: close button
      const closeBtn = createCloseButton(overlay);
      header.appendChild(closeBtn);

      // Pop-up box: content text
      const content = document.createElement('div');
      content.innerHTML = info_text;
      content.style.lineHeight = '1.3';
      dialog.appendChild(content);

      const footer = document.createElement('div');
      footer.id = 'chartInfoFooter';
      footer.style.cssText = `
        margin-top: 12px;
        font-size: 12px;
        text-align: left;
        width: 100%;
      `;
      footer.innerHTML = '<a href="https://chrismoreh.com" target="_blank" class="chart-info-footer-link">&copy; 2025 Moreh</a>';

      // Scoped footer styles (base colour + hover)
      const footerStyle = document.createElement('style');
      footerStyle.id = 'chartInfoFooterStyle';
      footerStyle.textContent = `
        .chart-info-footer-link {
          color: #555;
          text-decoration: none;
          transition: color 0.15s ease;
        }
        .chart-info-footer-link:hover {
          color: #a67c00;
        }
      `;
      dialog.appendChild(footerStyle);
      dialog.appendChild(footer);

      overlay.onclick = function(e) { if (e.target === overlay) overlay.remove(); };
      document.addEventListener('keydown', function esc(e) { if (e.key === 'Escape') { overlay.remove(); document.removeEventListener('keydown', esc); } });

      document.body.appendChild(overlay);
    };

    // Hover tooltip
    const tooltip = document.createElement('div');
    tooltip.innerHTML = `
      <div>${info_title}</div>
      <div style="font-family: Arial, sans-serif; font-size: 12px; color: #a67c00;">
        Click for more information
      </div>
    `;
    tooltip.style.cssText = `
      position: absolute;
      top: 8px;
      left: 40px;
      background: rgba(255, 255, 255, 1);
      color: #000;
      padding: 5px;
      border-radius: 6px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
      font-family: Arial, sans-serif;
      font-size: 18px;
      font-weight: bold;
      line-height: 1.3;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.2s ease;
      z-index: 9999;
    `;
    chart.container.appendChild(info);
    chart.container.appendChild(tooltip);
  }

  // ===== Period navigation =====

  // The chevrons and the period name live inside chart.container rather than in
  // page furniture around it, so that the whole widget can be dropped into
  // another page without its navigation being left behind.
  function makeNavButton(glyph, href, title) {
    const btn = document.createElement('a');
    btn.href = href;
    btn.textContent = glyph;
    btn.title = title;
    btn.style.cssText = `
      position: absolute;
      top: 7px;
      width: 26px;
      height: 26px;
      border-radius: 50%;
      background-color: #ffffff;
      border: 2px solid #000000ff;
      color: #000000ff;
      font-weight: bold;
      font-size: 18px;
      text-align: center;
      line-height: 25px;
      text-decoration: none;
      cursor: pointer;
      z-index: 9998;
      transition: all 0.2s ease;
      font-family: Arial, sans-serif;
    `;
    btn.onmouseover = function () {
      this.style.backgroundColor = '#d4af37';
      this.style.borderColor = '#d4af37';
      this.style.color = '#ffffff';
    };
    btn.onmouseout = function () {
      this.style.backgroundColor = '#ffffff';
      this.style.borderColor = '#000000ff';
      this.style.color = '#000000ff';
    };
    return btn;
  }

  function addPeriodNav(chart) {
    const cfg = window.SocTimeConfig;
    if (!cfg.periodLabel) return;
    if (document.getElementById('chartPeriodNav')) return;

    const strip = document.createElement('div');
    strip.id = 'chartPeriodNav';

    const name = document.createElement('a');
    name.href = cfg.indexHref || '#';
    name.textContent = cfg.periodLabel;
    name.title = 'All periods';
    name.style.cssText = `
      position: absolute;
      top: 8px;
      left: 50%;
      transform: translateX(-50%);
      font-family: Arial, sans-serif;
      font-size: 19px;
      letter-spacing: 0.04em;
      color: #000;
      text-decoration: none;
      z-index: 9998;
      transition: color 0.2s ease;
    `;
    name.onmouseover = function () { this.style.color = '#a67c00'; };
    name.onmouseout = function () { this.style.color = '#000'; };
    strip.appendChild(name);

    if (cfg.prevHref) {
      const prev = makeNavButton('‹', cfg.prevHref, 'Previous period: ' + cfg.prevLabel);
      prev.style.left = '42px';
      strip.appendChild(prev);
    }

    if (cfg.nextHref) {
      const next = makeNavButton('›', cfg.nextHref, 'Next period: ' + cfg.nextLabel);
      next.style.right = '12px';
      strip.appendChild(next);
    }

    chart.container.appendChild(strip);
  }

  // ===== Tradition membership =====
  // A point carries the tags of its person: the author label and the bar
  // directly, a publication through the join in SocTime.R. With no tradition
  // selected every point is in the active group.
  function inActiveGroup(chart, point) {
    if (chart.activeGroupId === null || chart.activeGroupId === undefined) return true;
    const tags = point.options.tags;
    if (!tags) return false;
    return Array.isArray(tags) ? tags.includes(chart.activeGroupId) : tags === chart.activeGroupId;
  }

  // The author label is HTML, so its opacity and its pointer events live on
  // the element that carries the markup rather than on the SVG wrapper that
  // Highcharts positions. Fading that inner element leaves the wrapper's own
  // opacity alone, which Highcharts resets when it checks labels for overlap.
  function labelNode(dataLabel) {
    return (dataLabel.text && dataLabel.text.element) || dataLabel.element;
  }

  function fadeLabel(dataLabel, opacity, active) {
    const node = labelNode(dataLabel);
    if (!node) return;
    node.style.opacity = opacity;
    node.style.pointerEvents = active ? '' : 'none';
    node.style.cursor = active ? 'pointer' : 'default';
  }

  // ===== Apply fading to grouping variable =====
  function applyGroupFade(chart) {

    chart.series.forEach(function (s) {

      // ---- EVENT SERIES: always visible, always interactive ----
      if (s.options.custom && s.options.custom.excludeFromGroupFade) {
        s.points.forEach(function(p) {
          if (p.graphic) {
            p.graphic.attr({ opacity: 1 });
            p.setState('');
          }
          if (p.dataLabel) {
            p.dataLabel.attr({ opacity: 1 });
          }
        });
        s.options.enableMouseTracking = true;
        return;
      }

      const isPublication = s.options.custom && s.options.custom.isPublication;
      const isAuthor = s.options.custom && s.options.custom.isAuthor;

      s.points.forEach(function (p) {
        const active = inActiveGroup(chart, p);
        const opacity = active ? 1 : 0.15;

        // The author point draws no marker, so its graphic is absent and only
        // the label is faded
        if (p.graphic) {
          p.graphic.attr({
            opacity: opacity,
            'pointer-events': active ? 'auto' : 'none'
          });
        }

        if (isAuthor && p.dataLabel) {
          fadeLabel(p.dataLabel, opacity, active);
        }

        // Clear hover state ONLY for non-publications
        if (!isPublication && p.graphic) {
          p.setState('');
        }
      });

      // ---- mouse tracking rules ----
      // Always keep tracking ON; control interactivity via pointer-events
      s.options.enableMouseTracking = true;

    });
  }

  // ===== HTML group selector overlay =====
  // The options come from the build, in vocabulary order and limited to the
  // traditions somebody on the page carries. With none there is nothing to
  // highlight, so the dropdown is not built and applyGroupFade() is never
  // reached: chart.activeGroupId stays null and every point keeps full opacity.
  function addGroupSelector(chart) {
    const cfg = window.SocTimeConfig;
    const traditions = cfg.traditions || [];
    if (traditions.length === 0) return;
    if (document.getElementById('hc-group-selector')) return;

    const container = document.createElement('div');
    container.id = 'hc-group-selector';

    // The previous-period chevron occupies the place the selector takes on
    // the full-span page, so on a page with a chevron the selector moves right
    if (cfg.prevHref) container.style.left = '80px';

    const select = document.createElement('select');
    select.id = 'hc-group-select';

    const placeholderOpt = document.createElement('option');
    placeholderOpt.value = '';
    placeholderOpt.textContent = 'Highlight a tradition';
    placeholderOpt.disabled = true;
    placeholderOpt.selected = true;
    placeholderOpt.hidden = true;
    select.appendChild(placeholderOpt);

    const resetOpt = document.createElement('option');
    resetOpt.value = '__ALL__';
    resetOpt.textContent = 'Highlight all';
    select.appendChild(resetOpt);

    traditions.forEach(function (t) {
      const opt = document.createElement('option');
      opt.value = t.id;
      opt.textContent = t.label;
      select.appendChild(opt);
    });

    // Apply group filtering
    select.addEventListener('change', function () {

      if (this.value === '__ALL__') {
        chart.activeGroupId = null;
        this.value = ''; // ← snap back to placeholder
      } else {
        chart.activeGroupId = this.value;
      }

      applyGroupFade(chart);
      chart.redraw(false);
    });

    // Prevent Highcharts interactions underneath
    container.addEventListener('mousedown', e => e.stopPropagation());
    container.addEventListener('click', e => e.stopPropagation());
    container.addEventListener('wheel', e => e.stopPropagation());

    container.appendChild(select);
    chart.container.appendChild(container);
  }

  // ===== Author labels: keep them on the page when the bar start is zoomed off =====
  // Highcharts aligns a data label to the plot position of its point and hides
  // the label when that position lies outside the plot area, so a bar whose
  // start has been zoomed off the left edge would lose its portrait and name.
  // For the author series the alignment pass therefore runs against the pixel
  // of max(point.x, axis.min): a label whose bar begins off-screen sits at the
  // left edge of the plot area, and every other label keeps its constant gap
  // before its bar. The pass runs inside every redraw, so no separate
  // repositioning step is needed and nothing flickers between hidden and shown.
  function clampAuthorLabels() {
    if (!window.Highcharts || !Highcharts.Series || Highcharts.Series.prototype.socTimeClamp) return;

    Highcharts.wrap(Highcharts.Series.prototype, 'alignDataLabel',
      function (proceed, point, dataLabel, options, alignTo, isNew) {
        const isAuthor = this.options.custom && this.options.custom.isAuthor;
        if (!isAuthor || !this.xAxis || typeof point.plotX !== 'number') {
          return proceed.apply(this, Array.prototype.slice.call(arguments, 1));
        }

        const axis = this.xAxis;
        const leftEdge = Math.max(0, axis.toPixels(axis.min, true));
        const plotX = point.plotX;

        if (plotX < leftEdge) point.plotX = leftEdge;
        proceed.call(this, point, dataLabel, options, alignTo, isNew);
        point.plotX = plotX;
      });

    Highcharts.Series.prototype.socTimeClamp = true;
  }

  clampAuthorLabels();

  // ===== Query-string zoom =====
  function applyQueryZoom(chart) {
    let params;
    try { params = new URLSearchParams(window.location.search); } catch (e) { return; }
    const from = parseInt(params.get('from'), 10);
    const to = parseInt(params.get('to'), 10);
    if (isNaN(from) || isNaN(to) || to <= from) return;

    // Without animation, so that a headless capture taken straight after load
    // shows the zoomed state rather than the first frame of the transition
    chart.xAxis[0].setExtremes(Date.UTC(from, 0, 1), Date.UTC(to, 11, 31), true, false);
    if (chart.showResetZoom) chart.showResetZoom();
  }

  // ===== Chart load handler =====
  function onChartLoad() {
    const chart = this;

    clampAuthorLabels();

    const originalRefresh = chart.tooltip.refresh;
    chart.tooltip.refresh = function (point, mouseEvent) {
      if (!point) return;

      const series = point.series;

      // Allow tooltips for excluded series (events)
      if (series.options.custom && series.options.custom.excludeFromGroupFade) {
        return originalRefresh.call(this, point, mouseEvent);
      }

      // Block tooltip for inactive group (authors/publications only)
      if (!inActiveGroup(chart, point)) {
        this.hide(0);
        return;
      }

      return originalRefresh.call(this, point, mouseEvent);
    };

    chart.activeGroupId = null;
    const axis = chart.yAxis[0];
    const totalCats = axis.categories.length;

    // ===== Scroll behaviour =====
    chart.container.addEventListener('wheel', function(e) {
      e.preventDefault();

      const range = axis.max - axis.min;
      const delta = e.deltaY > 0 ? -1 : 1;
      const step  = range * 0.1;

      let newMin = axis.min + delta * step;
      let newMax = axis.max + delta * step;

      if (newMin < 0) {
        newMin = 0;
        newMax = range;
      } else if (newMax > totalCats - 1) {
        newMax = totalCats - 1;
        newMin = newMax - range;
      }

      axis.setExtremes(newMin, newMax, true, false);
    });

    addInfoIconOverlay(chart);
    addPeriodNav(chart);

    setTimeout(function () {
      applyGroupFade(chart);
    }, 0);

    // Call after chart load
    addGroupSelector(chart);

    applyQueryZoom(chart);
  }

  // ===== Chart redraw handler =====
  function onChartRedraw() {
    const chart = this;
    if (chart.activeGroupId === null || chart.activeGroupId === undefined) return;

    requestAnimationFrame(function () {
      applyGroupFade(chart);
    });
  }

  // ===== Lifespan bars: tooltip =====
  // The bar is the whole life, so the tooltip gives the name and the life dates.
  function lifespanTooltipFormatter() {
    const lifeFrom = this.birth ? Highcharts.dateFormat('%Y', this.birth) : '';
    const lifeTo = this.living ? '' : (this.death ? Highcharts.dateFormat('%Y', this.death) : '');

    let out = '<b>' + this.author + '</b>';
    if (lifeFrom || lifeTo) out += ' (' + lifeFrom + '–' + lifeTo + ')';
    return out;
  }

  // ===== Author series: data label =====
  // The surname and the portrait, as one piece of HTML aligned so that its
  // right edge sits a fixed number of pixels before the bar start. Where no
  // portrait file exists a grey circle of the same size carries the initials,
  // so that adding author_photos/<id>.png and rebuilding is all a photo takes.
  //
  // Highcharts passes HTML labels through its sanitiser, which keeps an image
  // source only when it begins with a scheme, `/`, `./` or `../`, and drops
  // every attribute it does not know. The relative path from the build is
  // therefore prefixed with `./`, and nothing is hung on data attributes.
  function authorLabelFormatter() {
    const o = this.point.options;
    const size = window.SocTimeConfig.portraitPx || 37;

    let src = o.image_circle || '';
    if (src && !/^(\.|\/|[a-z]+:)/i.test(src)) src = './' + src;

    const portrait = src
      ? '<img class="soctime-portrait" src="' + src + '" width="' + size +
        '" height="' + size + '">'
      : '<span class="soctime-initials" style="width:' + size + 'px;height:' + size + 'px;">' +
        (o.initials || '') + '</span>';

    return '<span class="soctime-author">' +
           '<span class="soctime-surname">' + (o.surname || '') + '</span>' +
           portrait + '</span>';
  }

  // ===== Author series: point events =====
  // Highcharts registers the data-labels group of a series as a tracker, so a
  // pointer over the HTML label reaches the point's own mouseOver, mouseOut and
  // click events; nothing has to be delegated by hand. The point draws no
  // marker, so `this.graphic` is normally absent.
  function authorMouseOver() {
    const chart = this.series.chart;
    if (!inActiveGroup(chart, this)) return;
    if (this.graphic) this.graphic.attr({ cursor: 'pointer' });
  }

  function authorMouseOut() {
    if (this.graphic) this.graphic.attr({ cursor: 'default' });
  }

  function authorClick() {
    const chart = this.series.chart;
    if (!inActiveGroup(chart, this)) return;

    var author = this.options.author_long || this.options.author;
    var bio = this.options.bio || '';
    var img = this.options.image_sq || '';

    // Format birth/death info
    var birthYear = this.options.birth ? Highcharts.dateFormat('%Y', this.options.birth) : '';
    var deathYear = (!this.options.living && this.options.death) ? Highcharts.dateFormat('%Y', this.options.death) : '';
    var pob = this.options.pob || '';
    var pod = this.options.living ? '' : (this.options.pod || '');

    var lifeInfo = '';
    if (birthYear || deathYear || pob || pod) {
      lifeInfo = '' +
        [birthYear, pob].filter(Boolean).join(', ') +
        ' – ' +
        [deathYear, pod].filter(Boolean).join(', ') +
        '';
    }

    // Create overlay
    var overlay = document.createElement('div');
    overlay.id = 'bioOverlay';
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.5);
      z-index: 9990;
      display: flex;
      align-items: center;
      justify-content: center;
    `;

    // Create dialog
    var dialog = document.createElement('div');
    dialog.style.cssText = `
      background: #fff;
      padding: 20px;
      border-radius: 10px;
      max-width: 600px;
      max-height: 80%;
      overflow-y: auto;
      box-shadow: 0 4px 20px rgba(0,0,0,0.2);
      position: relative;
      text-align: justify;
    `;

    // Header
    var header = document.createElement('div');
    header.style.cssText = `
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1px;
    `;
    var title = document.createElement('h3');
    title.textContent = author;
    title.style.margin = '0';

    // Close button
    const closeBtn = createCloseButton(overlay);

    header.appendChild(title);
    header.appendChild(closeBtn);

    // Add biographical note line
    var lifeLine = document.createElement('div');
    lifeLine.textContent = lifeInfo;
    lifeLine.style.cssText = `
      font-size: 0.9rem;
      color: #555;
      font-style: italic;
      margin-bottom: 10px;
    `;

    // Content container
    var content = document.createElement('div');
    content.style.cssText = 'line-height: 1.3;';

    if (img !== '') {
      var imageElem = document.createElement('img');
      imageElem.src = img;
      imageElem.style.cssText = `
        float: right;
        margin: 0 0 10px 10px;
        max-width: 200px;
        max-height: 200px;
        border-radius: 5px;
      `;
      content.appendChild(imageElem);
    }

    var bioElem = document.createElement('div');
    bioElem.innerHTML = bio;
    content.appendChild(bioElem);

    dialog.appendChild(header);
    dialog.appendChild(lifeLine);
    dialog.appendChild(content);
    overlay.appendChild(dialog);

    // Close on background click or ESC
    overlay.onclick = function(e) { if (e.target === overlay) overlay.remove(); };
    document.addEventListener('keydown', function esc(e) {
      if (e.key === 'Escape') {
        overlay.remove();
        document.removeEventListener('keydown', esc);
      }
    });

    document.body.appendChild(overlay);
  }

  // ===== Author series: tooltip =====
  function authorTooltipFormatter() {
    const chart = this.series.chart;
    if (!inActiveGroup(chart, this)) return;

    // The labels carry the precision of the front matter (a year alone for most
    // of the medieval cast); the millisecond values are for drawing only
    const died = this.living
      ? ''
      : 'Died: ' + (this.death_label || Highcharts.dateFormat('%d %b %Y', this.death)) + ' in ' + this.pod + '<br>';

    return '<b>' + (this.author_long || this.author) + '</b><br>' +
          'Born: ' + (this.birth_label || Highcharts.dateFormat('%d %b %Y', this.birth)) + ' in ' + this.pob + '<br>' +
          died +
          '<span style="font-family: Arial, sans-serif; font-size: 12px; color: #a67c00;">Click for a biography</span>';
  }

  // ===== Publications series: point events =====
  function pubMouseOver() {
    const chart = this.series.chart;
    const point = this;

    // Fade book icons according to hover
    chart.series.forEach(function(s) {
      if (!s.options.custom || !s.options.custom.isPublication) return;

      s.points.forEach(function(p) {
        if (!p.graphic) return;

        // Hovered book at full opacity, every other book dimmed
        p.graphic.attr({ opacity: (p === point ? 1 : 0.2) });
      });
    });

    if (this.graphic) this.graphic.attr({ cursor: 'pointer' });
  }

  function pubMouseOut() {
    const chart = this.series.chart;

    // Reset opacity
    chart.series.forEach(function(s) {
      if (!s.options.custom || !s.options.custom.isPublication) return;

      s.points.forEach(function(p) {
        if (!p.graphic) return;

        p.graphic.attr({ opacity: 1 });
      });
    });
  }

  function pubClick() {
    var orig_title = this.options.orig_title || this.options.work || '';
    var author = this.options.author || '';
    var coauthor = this.options.coauthor || '';
    var pub_date = this.options.pub_date || '';
    var eng_title = this.options.eng_title || '';
    var eng_date = this.options.eng_date || '';
    var summary = this.options.summary || '';

    // Convert pub_date (e.g. 1762-01-01) to just the year
    var pub_year = '';
    if (pub_date) {
      var match = pub_date.match(/\d{4}/);
      if (match) pub_year = match[0];
    }

    // Remove any existing overlay first
    var existing = document.getElementById('bioOverlay');
    if (existing) existing.remove();

    // Create overlay
    var overlay = document.createElement('div');
    overlay.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9990; display: flex; align-items: center; justify-content: center;';

    // Create dialog
    var dialog = document.createElement('div');
    dialog.style.cssText = 'background: rgba(250,250,250,0.95); padding: 20px; border-radius: 10px; max-width: 700px; max-height: 80%; overflow-y: auto; box-shadow: 0 4px 20px rgba(0,0,0,0.2); position: relative; text-align: justify; font-family: Arial, sans-serif; font-size: 14px;';

    // Title header
    var header = document.createElement('div');
    header.style.cssText = 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 0px;';
    var title = document.createElement('h3');
    title.textContent = orig_title;
    title.style.margin = '0';
    // Close button
    const closeBtn = createCloseButton(overlay);

    header.appendChild(title);
    header.appendChild(closeBtn);

    // Content container
    var content = document.createElement('div');
    content.style.cssText = 'line-height: 1.3;';

    // Publication metadata
    var PublicationMeta = document.createElement('div');

    if (coauthor) {
    var PublicationMetaText = author + ' and ' + coauthor + ', ' + pub_year;
    } else if (author) {
    var PublicationMetaText = author + ', ' + pub_year;
    }
    if (eng_title.trim() !== '' && eng_date.trim() !== '') {
      PublicationMetaText += '<br>First published in English in ' + eng_date + ' as <i>' + eng_title + '</i>.';
    } else if (eng_title.trim() !== '') {
      PublicationMetaText += '<br>Title in English: <i>' + eng_title + '</i>.';
    } else if (eng_date.trim() !== '') {
      PublicationMetaText += '<br>First published in English in ' + eng_date + '.';
    }

    PublicationMeta.innerHTML = PublicationMetaText;

    PublicationMeta.style.cssText = `
      font-size: 0.9rem;
      color: #555;
      font-style: normal;
      margin-bottom: 5px;
    `;

    content.appendChild(PublicationMeta);

    // Add a small spacing before summary
    var spacer = document.createElement('div');
    spacer.style.height = '0px';
    content.appendChild(spacer);

    // Summary text
    var summaryElem = document.createElement('div');
    summaryElem.innerHTML = summary;
    content.appendChild(summaryElem);

    // Assemble dialog
    dialog.appendChild(header);
    dialog.appendChild(content);
    overlay.appendChild(dialog);

    // Close behavior
    overlay.onclick = function(e) {
      if (e.target === overlay) overlay.remove();
    };
    document.addEventListener('keydown', function esc(e) {
      if (e.key === 'Escape') {
        overlay.remove();
        document.removeEventListener('keydown', esc);
      }
    });

    document.body.appendChild(overlay);
  }

  // ===== Publications series: tooltip =====
  function pubTooltipFormatter() {
    var engInfo = '';
    if (this.eng_title && this.eng_title.toString().trim() !== '') {
      if (this.eng_date && this.eng_date.toString().trim() !== '') {
        engInfo = "<span class='lang-flag'>EN</span> <b>" + this.eng_title + ' (' + this.eng_date + ')</b><br>';
      } else {
        engInfo = "<span class='lang-flag'>EN</span> <b>" + this.eng_title + '</b><br>';
      }
    }
    return this.orig_language + ' <b>' + (this.orig_title || '') + ' (' + Highcharts.dateFormat("%Y", this.x) + ')</b><br>' + engInfo + '<span style="font-family: Arial, sans-serif; font-size: 12px; color: #a67c00;">Click for a summary</span>';
  }

  // ===== X-axis: label formatter =====
  // Only the full-span page carries a cutoff year, for the compressed gutter at
  // its left edge; a period page starts where its first tick starts and prints
  // every year plainly.
  function xAxisLabelFormatter() {
    var cutoffYear = window.SocTimeConfig.labelCutoffYear;
    var year = new Date(this.value).getUTCFullYear();

    if (cutoffYear === null || cutoffYear === undefined) return year;

    var cutoffMs = Date.UTC(cutoffYear, 0, 1);

    if (year < cutoffYear) {
      return ''; // hide label, keep tick
    } else {
      // Find the first tick position at/after the cutoff year
      var positions = (this.axis.tickPositions || []).filter(function(t) {
        return t >= cutoffMs;
      });
      var firstPos = positions.length ? positions[0] : null;
      if (firstPos !== null && this.value === firstPos) {
        return '⋯'; // show middle-dot ellipsis for first visible year
      }
      return year;
    }
  }

  // ===== X-axis: tick positioner =====
  // Ticks sit on 1 January of every year that is a multiple of the page's tick
  // spacing. Positions spaced by a fixed number of milliseconds drift a day per
  // four years from the 1970 epoch, so that a tick meant for 1980 falls on
  // 30 December 1979 and is labelled with the wrong year
  function xAxisTickPositioner(min, max) {
    var cutoffYear = window.SocTimeConfig.labelCutoffYear;
    var years = window.SocTimeConfig.tickYears ||
      Math.max(1, Math.round(window.SocTimeConfig.tickIntervalMs / (365 * 864e5)));
    var first = Math.ceil(new Date(min).getUTCFullYear() / years) * years;
    var last = new Date(max).getUTCFullYear();
    var positions = [];
    for (var y = first; y <= last; y += years) positions.push(Date.UTC(y, 0, 1));
    if (cutoffYear === null || cutoffYear === undefined) return positions;
    positions = positions.filter(function(t) {
      return new Date(t).getUTCFullYear() >= cutoffYear;
    });
    return positions;
  }

  // ===== Events series: point events =====
  function eventMouseOver() {
    const chart = this.series.chart;
    if (chart.activeHoverBand) { chart.xAxis[0].removePlotBand(chart.activeHoverBand); }
    if (this.start && this.end) {
      let bandColour = 'rgba(255,0,0,0.1)';
      if (this.series.name === 'Political revolutions') bandColour = 'rgba(158, 17, 17, 0.2)';
      else if (this.series.name === 'Ideational revolutions') bandColour = 'rgba(12, 125, 27, 0.2)';
      else if (this.series.name === 'Technological revolutions') bandColour = 'rgba(12, 27, 125, 0.2)';
      chart.xAxis[0].addPlotBand({
        id: 'hoverBand_' + this.index,
        from: this.start,
        to: this.end,
        color: bandColour,
        zIndex: 0   // ensure band is behind axis labels
      });
      chart.activeHoverBand = 'hoverBand_' + this.index;
    }

    this.graphic.attr({ cursor: 'pointer' });
  }

  function eventMouseOut() {
    this.graphic.attr({ cursor: 'default' });
  }

  function eventClick() {
    var event = this.options.event_name;
    var description = this.options.description || '';

    // Remove any existing overlay
    var existing = document.getElementById('bioOverlay');
    if (existing) existing.remove();

    // Create overlay
    var overlay = document.createElement('div');
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.5);
      z-index: 9990;
      display: flex;
      align-items: center;
      justify-content: center;
    `;

    // Dialog
    var dialog = document.createElement('div');
    dialog.style.cssText = `
      background: rgba(250,250,250,0.9);
      padding: 20px;
      border-radius: 10px;
      max-width: 600px;
      max-height: 80%;
      overflow-y: auto;
      box-shadow: 0 4px 20px rgba(0,0,0,0.2);
      position: relative;
      text-align: justify;
    `;

    // Header
    var header = document.createElement('div');
    header.style.cssText = 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;';
    var title = document.createElement('h3');
    title.innerHTML = event;
    title.style.margin = '0';

    // Close button
    const closeBtn = createCloseButton(overlay);

    header.appendChild(title);
    header.appendChild(closeBtn);

    // Content
    var content = document.createElement('div');
    content.style.cssText = 'line-height: 1.3;';
    var descElem = document.createElement('div');
    descElem.innerHTML = description;
    content.appendChild(descElem);

    dialog.appendChild(header);
    dialog.appendChild(content);
    overlay.appendChild(dialog);

    // Close behavior
    overlay.onclick = function(e) { if (e.target === overlay) overlay.remove(); };
    document.addEventListener('keydown', function esc(e) {
      if (e.key === 'Escape') { overlay.remove(); document.removeEventListener('keydown', esc); }
    });

    document.body.appendChild(overlay);
  }

  // ===== Events series: tooltip =====
  function eventTooltipFormatter() {
    return '<b>' + this.event_name + '</b><br>' +
           '<span style="font-family: Arial, sans-serif; font-size: 12px; color: #a67c00;">Click for details</span>';
  }

  return {
    onChartLoad: onChartLoad,
    onChartRedraw: onChartRedraw,
    applyGroupFade: applyGroupFade,
    applyQueryZoom: applyQueryZoom,
    addInfoIconOverlay: addInfoIconOverlay,
    addPeriodNav: addPeriodNav,
    createCloseButton: createCloseButton,
    lifespanTooltipFormatter: lifespanTooltipFormatter,
    authorLabelFormatter: authorLabelFormatter,
    authorMouseOver: authorMouseOver,
    authorMouseOut: authorMouseOut,
    authorClick: authorClick,
    authorTooltipFormatter: authorTooltipFormatter,
    pubMouseOver: pubMouseOver,
    pubMouseOut: pubMouseOut,
    pubClick: pubClick,
    pubTooltipFormatter: pubTooltipFormatter,
    xAxisLabelFormatter: xAxisLabelFormatter,
    xAxisTickPositioner: xAxisTickPositioner,
    eventMouseOver: eventMouseOver,
    eventMouseOut: eventMouseOut,
    eventClick: eventClick,
    eventTooltipFormatter: eventTooltipFormatter
  };

})();
